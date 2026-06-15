# UNIFY — Recherche d'emploi menée par IA (MCP-first)

> Guide d'architecture et d'implémentation pour faire coopérer
> **proton-mail-bridge**, **jobber** et **idae-machine** afin qu'un agent LLM
> (Claude) conduise lui-même la recherche d'emploi : lire les alertes email, en
> extraire les offres, scorer le fit, persister et trier — **sans UI**.
> L'interface est l'**agent + trois serveurs MCP**. Aucune base SQLite : le
> store est la base **MongoDB d'idae-machine**, pilotée par son **MCP**.
> D'idae-machine on utilise **le MCP et la DB uniquement — jamais les composants
> UI** (différés tant que le front n'est pas fini).

---

## 1. Principe

L'agent est l'orchestrateur. Il enchaîne des **outils MCP** guidé par une
**skill** qui porte la méthodologie (domaines expéditeurs, recettes IMAP,
heuristiques de pré-filtrage). Trois serveurs MCP, une seule base :

- **mail** ← `protonesk` (proton-mail-bridge) : I/O ProtonMail via hydroxide.
- **compute** ← `jobber` (à créer) : parse CV, extraction d'offres depuis le HTML
  d'un email, scoring sémantique (Ollama). Sans état, sans DB.
- **data** ← `idae-machine` MCP : CRUD/validation/RBAC/audit sur MongoDB, modèle
  `jobberScheme` déjà publié. C'est le store unique.

Décision : **MCP-only, store = idae-machine**. jobber ne stocke plus rien
lui-même ; il calcule. La persistance, la dédup, le tri, l'historique vivent
dans Mongo via le MCP idae-machine (mêmes hooks/validation/audit que le REST).

---

## 2. Les trois briques et leur rôle

| Brique | Nature | Rôle UNIFY | Statut |
|---|---|---|---|
| **proton-mail-bridge** (`protonesk`) | MCP Node/TS sur hydroxide (IMAP/SMTP local) | **Entrée mail** : recherche + lecture des alertes emploi | Opérationnel |
| **jobber** | Modules Python (parser CV, extraction JD, matcher Ollama) | **Compute** : `profile_parse`, `extract_jobs_from_email`, `score_job` — exposés en MCP | Pivot email (`NEXT.md`) ; **MCP à écrire** |
| **idae-machine** | Serveur Express/MongoDB + **MCP 44 outils** (`/api/mcp`), schéma-driven | **Store + accès données** : persiste/dédup/trie via Mongo ; modèle `jobberScheme` + seed prêts | MCP & DB opérationnels ; **UI non utilisée** |

Frontière nette : `protonesk` ne sait rien de l'emploi ; `jobber` ne parle ni
IMAP ni Mongo (il calcule) ; `idae-machine` ne fait pas de métier (il valide,
stocke, sert).

---

## 3. Architecture cible

```
                         ┌──────────────────────────────┐
                         │   Agent LLM (Claude Code)     │
                         │   + skill: imap-job-search    │
                         └───────────────┬──────────────┘
                                outils MCP│
        ┌───────────────────────┬─────────┴──────────────┬─────────────────────┐
        ▼                       ▼                          ▼
┌────────────────┐   ┌────────────────────────┐   ┌──────────────────────────────┐
│ MCP: protonesk │   │ MCP: jobber (NOUVEAU)  │   │ MCP: idae-machine (DATA)       │
│   (mail I/O)   │   │   compute, sans état    │   │   POST /api/mcp  (HTTP)        │
│                │   │                         │   │   Bearer mk_jobber_…           │
│ search_messages│   │ profile_parse           │   │                                │
│ get_message    │   │ extract_jobs_from_email │   │ find / find_one / get_by_id    │
│ list_messages  │   │ score_job               │   │ create / update / update_by_id │
│ mark/move      │   │                         │   │ count / aggregate / resolve_fks│
└───────┬────────┘   └───────────┬─────────────┘   └───────────────┬────────────────┘
        │ IMAP/SMTP              │ Ollama (local)                   │ Mongoose
        ▼                        ▼                                  ▼
 hydroxide (ProtonMail)   ollama serve                    MongoDB  jobber_machine_{app,user,base}
```

idae-machine est le **store**. jobber est un **coprocesseur** sans persistance.
L'agent fait la couture : il lit le HTML (protonesk) → calcule (jobber) →
écrit/lit (idae-machine).

---

## 4. Modèle de données — `jobberScheme`

Déjà écrit et déployable : `idae-machine/server/src/models/jobber/jobberScheme.ts`
(modèle `jobberScheme` + données `jobberSeed`). 16 collections. Le seed contient
le **vrai profil** (Meddy Lebrun) + référentiels + taxonomie de compétences ;
seules 2 offres préfixées `TEST —` existent (supprimables). Aucune offre réelle
n'est seedée : elles arrivent par le pipeline email.

Graphe :

```
  profile ──< profile_skill >── skill                 (référentiels: job_status,
     │                            │                     job_source, contract_type,
  match_result >── job ──< job_skill                    seniority, match_method,
     │              │  └──< job_event                    skill_kind, event_type)
     │              ├── company
     │              └── email_message ── job_source
```

Collections clés :

- **`profile`** / **`profile_skill`** — candidat scoré (un `active:true`).
- **`email_message`** — un message traité ; `message_id` = clé de dédup, `processed`.
- **`job`** — l'offre ; `link` (URL canonique) = dédup ; `score`/`gaps`
  dénormalisés pour tri ; FK `job_status` **requise** (défaut `new`=id 1).
- **`match_result`** — un scoring (score, model, strengths, gaps) lié à `job`+`profile`.
- **`job_skill`** — compétences de l'offre typées par `skill_kind` (required|matched|missing|detected).
- **`job_event`** — timeline de triage (status_change, note, applied…).

FK = id de la cible (cf. seed : `job_status: 2`, `job_source: 1`…). Les
référentiels sont seedés avec des ids stables (`job_status` 1=new … 8=offer).

> jobber **n'a pas** de schéma local. Ce fichier est la source de vérité du
> modèle. UNIFY mappe les anciens noms plats (`jobs.url`→`job.link`,
> `jobs.found_at`→`job.discovered_at`, etc., annotés dans le fichier).

---

## 5. Flux — « recherche menée par IA »

Boucle pilotée par l'agent (détails dans la skill). Appels MCP réels :

1. **Curseur** — dernier run :
   `idae.find_one(collection:"email_message", sort:{received_at:-1})` → date de reprise.
2. **Découverte** — `protonesk.search_messages` avec critère skill
   (`FROM jobs-noreply@linkedin.com`, `SINCE <curseur>`, `SUBJECT alert`…).
3. **Pré-filtre** — l'agent écarte le bruit (heuristiques skill) avant tout coût lourd.
4. **Dédup message** — pour chaque candidat :
   `idae.find_one(collection:"email_message", query:{message_id})`. Si présent et
   `processed:true` → skip.
5. **Lecture** — `protonesk.get_message` → HTML.
6. **Trace message** — `idae.create(collection:"email_message", data:{code:message_id, message_id, sender, sender_domain, subject, received_at, job_source:<id>, processed:false})`.
7. **Extraction** — `jobber.extract_jobs_from_email(html, source_hint)` → 1..N offres
   (digests LinkedIn/Indeed/WTTJ = 5-20 offres/mail).
8. **Dédup offre** — `idae.find_one(collection:"job", query:{link})`. Existant → skip.
9. **Scoring** — `jobber.score_job(profile, job)` → `{score, summary, strengths, gaps, skills[]}`
   (le profil vient de l'étape 0bis, voir §6).
10. **Persistance** (ordre FK : cibles avant dépendants) :
    - `idae.find_one`/`create` `company` si absente → id.
    - `idae.create(collection:"job", data:{code, name:title, title, location, link, message_id, description, score, gaps, job_status:1, job_source:<id>, company:<id>, email_message:<id>, ...})` → `jobId`.
    - `idae.create(collection:"match_result", data:{job:jobId, profile:<id>, match_method:1, model, score, summary, strengths, gaps})`.
    - `idae.create(collection:"job_skill", data:{...})` par compétence (skill_kind matched/missing/required).
    - `idae.create(collection:"job_event", data:{job:jobId, event_type:1, new_status:1, at:now, note})`.
11. **Clôture message** — `idae.update_by_id(collection:"email_message", id:<id>, data:{processed:true, job_count:N})` puis option `protonesk.move_message` vers dossier traité.
12. **Restitution** — `idae.find(collection:"job", query:{job_status:1}, sort:{score:-1}, limit)` →
    l'agent résume les nouveaux matchs triés ; l'utilisateur fixe le statut.
13. **Triage** — sur action utilisateur : `idae.update_by_id(collection:"job", id:jobId, data:{job_status:<id>})`
    + `idae.create(collection:"job_event", data:{job, event_type:1, new_status})`.

L'agent décide quand relancer (quotidien), comment éviter le retraitement
(`email_message.processed` + dédup `job.link`), quoi remonter.

---

## 6. MCP `jobber` (à créer — seule brique manquante)

Wrapper **mince** MCP autour des modules Python existants. **Aucune persistance**
(c'est le job d'idae-machine). Transport **stdio**, SDK Python `mcp`.

`src/mcp_server.py` :

```python
from mcp.server.fastmcp import FastMCP
from . import parser, jd_email_extractor, matcher

mcp = FastMCP("jobber")

@mcp.tool()
def profile_parse(resume_path: str, mask_pii: bool = True) -> dict:
    "Parse un CV (PDF/Docx) en profil JSON. NE persiste pas — l'agent écrit via idae-machine."
    return parser.parse(resume_path, mask_pii=mask_pii)

@mcp.tool()
def extract_jobs_from_email(html: str, source_hint: str = "") -> list[dict]:
    "Extrait 1..N offres du HTML d'un email d'alerte (digest géré). Sortie alignée sur la collection `job`."
    return jd_email_extractor.extract(html, source_hint)

@mcp.tool()
def score_job(profile: dict, job: dict) -> dict:
    "Score fit vs profil (Ollama). Sortie: {score, summary, strengths, gaps, skills:[{code,kind}]}."
    return matcher.score(profile, job)

if __name__ == "__main__":
    mcp.run()  # stdio
```

| Outil | Entrée | Sortie | Effet |
|---|---|---|---|
| `profile_parse` | `resume_path`, `mask_pii` | profil JSON | pur (CPU) |
| `extract_jobs_from_email` | `html`, `source_hint` | `[job]` | pur |
| `score_job` | `profile`, `job` | `{score, summary, strengths, gaps, skills[]}` | Ollama local |

Le profil n'est plus géré côté jobber : il est lu une fois par l'agent via
`idae.find_one(collection:"profile", query:{active:true})` puis passé à
`score_job`. `profile_parse` ne sert qu'à (re)peupler la collection `profile`
quand le CV change — l'agent persiste le résultat via `idae.update_by_id`.

`extract_jobs_from_email` = refactor de l'ancien `jd_analyzer.py` (entrée HTML
email au lieu d'une page web fetchée). `score_job` = `matcher.py` existant.

---

## 7. MCP `idae-machine` (store — déjà opérationnel)

- **Endpoint** : `POST http://<host>:<PORT>/api/mcp`. **`host`+`PORT` env-driven, pas
  fixes** — l'URL du `.mcp.json` doit matcher le serveur réellement lancé :
  - **dev** (`server: npm run dev` = `tsx --watch src/index.ts`) → `server/.env` `PORT=7842`,
    host `localhost`. Défaut code = `process.env.PORT || 7842` (= `DEFAULT_API_PORT` client).
  - **build/prod** (`npm run build` = `tsc` puis `npm start` = `node dist/index.js`) → même
    binaire, **PORT pris de l'env** ; le template `server/.env.example` met `PORT=3000`, et
    l'hôte peut être un domaine déployé. Côté client SvelteKit, override via `PUBLIC_API_URL`.
  - Conséquence : après un changement de PORT/host, **mettre à jour l'URL `idae` du `.mcp.json`**.
- **Transport** : Streamable HTTP stateless ; réponse en frame SSE (`data:` line à stripper) ; le `text` du résultat est une **string JSON** à reparser.
- **Auth** : `Authorization: Bearer <JWT | mk_jobber_…>`. L'org est encodée dans le préfixe de la clé → le resolver vise la bonne base sans session.
- **Outils consommés** (signatures vérifiées sur le serveur live) :
  - `find` { collection, query?, limit?, skip?, sort?, projection? }
  - `find_one` { collection, query }
  - `get_by_id` { collection, id }
  - `count` { collection, query? }
  - `create` { collection, **data** }   ← clé `data`, **pas** `record`
  - `update` { collection, query, **data** }
  - `update_by_id` { collection, id, **data** }   ← `data`, pas `patch`
  - `delete_by_id` { collection, id, permanent? }
  - `aggregate`, `resolve_fks`, `health`
- **FK** : passées par **id cible** (ex. `job_status:1`) ; le serveur résout et
  renvoie un objet `fks` enrichi dans la réponse (déjà constaté e2e).
- **Garde-fous** : writes ≡ REST (validation + hooks FK + audit) ; soft-delete par
  défaut ; aggregate whitelistée (`$lookup`/`$out` bloqués) ; cap 1000/appel.

**Pré-filtrage utile côté serveur** (économise des tours LLM) :
`idae.count(collection:"job", query:{job_status:1})`,
`idae.aggregate` pour grouper par `job_source` / fenêtre de score.

---

## 8. MCP `protonesk` (mail — déjà opérationnel)

Outils consommés : `search_messages` (FROM/SUBJECT/SINCE), `get_message` (HTML),
`list_messages`/`list_folders`, `mark_message`/`move_message` (anti-retraitement).
Pré-requis : hydroxide lancé + authentifié (Scheduled Task Windows) ;
connexion `tls.rejectUnauthorized:false` (cert local).

---

## 9. Skill `imap-job-search` (méthodologie)

Couche savoir non-code chargée par l'agent. Contenu :

- **Domaines/sujets par board** (alignés sur `job_source` seedé) : `linkedin.com`,
  `indeed.com`, `welcometothejungle.com`, `glassdoor.com`, patterns recruteurs —
  maintenus quand les boards changent leurs templates.
- **Recettes IMAP** : combinaisons `SINCE`/`FROM`/`SUBJECT`, dossier/label cible.
- **Digests vs offre unique** : comment éclater un mail multi-offres.
- **Pré-filtre** : ce qui mérite `score_job` (coûteux) avant de l'appeler.
- **Mapping référentiels** : sender_domain → `job_source.id` ; mots-clés titre →
  `seniority`/`contract_type` ; normalisation compétences → `skill.code`/`aliases`.
- **Cadence agent** : quand relancer, dédup (`email_message.processed`/`job.link`),
  comment résumer les nouveaux matchs.

La skill n'exécute pas de code : elle oriente l'enchaînement protonesk → jobber → idae-machine.

---

## 10. Bootstrap & configuration

**1. Déployer le modèle + seed dans Mongo** (une fois) :
```bash
cd D:/development/idae/packages/idae-machine
npx tsx server/src/bootstrap/bootstrap.ts jobber
# résout jobberScheme + jobberSeed → publie le modèle et seed
# dans jobber_machine_app / jobber_machine_user / jobber_machine_base
```

**2. Lancer le serveur idae-machine sur l'org jobber** (`server/.env`) :
```env
MONGODB_URI=mongodb://admin:<pwd>@localhost:27017
ORG=jobber
PORT=7842                   # dev ; prod template (.env.example) = 3000 → adapter l'URL .mcp.json
JWT_SECRET=<change-me>
AUTH_DISABLED=false        # true seulement pour exploration locale
MCP_SCHEMA_WRITE=false     # garder off : pas de mutation de schéma via MCP
```
```bash
# dev (hot-reload)
cd server && npm run dev          # tsx --watch src/index.ts → port 7842
# build/prod
cd server && npm run build && npm start   # tsc → node dist/index.js → port = $PORT
```
> `dotenv` n'override pas l'env déjà présent : `$env:ORG`/`$env:AUTH_DISABLED` passés au
> lancement priment sur `server/.env` (utile pour basculer org/auth sans éditer le fichier).

**3. Mint une clé API agent** (via le MCP idae-machine, voir MCP-GUIDE) :
```
auth_login(login:"admin", password:"admin123")  → JWT
apikey_create(name:"jobber-agent")               → mk_jobber_xxxx   (avec le JWT)
```
La clé n'est rendue **qu'une fois**. La minter en tant qu'utilisateur réel
(pas sous `AUTH_DISABLED`, sinon owner `dev` ne résout pas).

**4. proton-mail-bridge** (`.env`) :
```env
HYDROXIDE_HOST=127.0.0.1
HYDROXIDE_IMAP_PORT=1143
HYDROXIDE_SMTP_PORT=1025
HYDROXIDE_USER=<proton-user>
HYDROXIDE_PASSWORD=<bridge-password de `hydroxide auth`>
```

**5. Enregistrer les trois MCP** (config agent, ex. `.mcp.json`) :
```json
{
  "mcpServers": {
    "protonesk": {
      "command": "node",
      "args": ["D:/development/proton-mail-bridge/dist/index.js"]
    },
    "jobber": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "D:/development/jobber"
    },
    "idae": {
      "type": "http",
      "url": "http://localhost:7842/api/mcp",
      "headers": { "Authorization": "Bearer mk_jobber_xxxx" }
    }
  }
}
```

> L'URL `idae` ci-dessus (`localhost:7842`) = **dev**. En build/prod, remplacer par
> `http://<host>:<PORT>/api/mcp` selon le serveur lancé (cf. §7).

Liveness : `idae.health` (public) → `{status, org:"jobber", flags}`.

---

## 11. État & reste à faire

### Fait (vérifié e2e le 2026-06-13)

- ✅ **Modèle idae-machine** : `jobberScheme` + `jobberSeed` (16 collections, profil réel,
  45 skills, référentiels). Source : `idae-machine/server/src/models/jobber/jobberScheme.ts`.
- ✅ **Bootstrap** : `npx tsx src/bootstrap/bootstrap.ts jobber` (depuis `server/`,
  URI Mongo via `server/.env`) → publie + seed dans `jobber_machine_{app,user,base}`.
- ✅ **Serveur idae-machine** : démarre sur `ORG=jobber`, MCP `/api/mcp` répond (`health` → org=jobber).
- ✅ **MCP store prouvé** : `find`/`find_one`/`count`/`create`/`delete_by_id` OK ;
  FK passées par id, résolues côté serveur (objet `fks` en retour).
- ✅ **jobber compute** : `src/jd_email_extractor.py` (refactor email), `src/parser.py`
  (→ `profile_parse`), `src/matcher.py` (→ `score_job`).
- ✅ **jobber MCP** : `src/mcp_server.py` (stdio, 3 outils), dépendance `mcp` dans `requirements.txt`.
- ✅ **Tests** : `tests/test_jd_email_extractor.py` + `tests/test_mcp_server.py` → 20/20.
- ✅ **Skill** : `skills/imap-job-search/SKILL.md`.

### Reste à faire (pour la boucle live)

1. ✅ **Auth réelle idae-machine** : serveur lancé `ORG=jobber` + `AUTH_DISABLED=false` ;
   `auth_login(admin/admin123)` → JWT → `apikey_create("jobber-agent")` →
   **`mk_jobber_8e97…`** (vérifié `auth_whoami` : admin, org=jobber, bearer).
   Clé sauvée dans `D:/development/jobber/.idae-agent-key` (secret — ne pas committer).
   Note : serveur lancé via `$env:ORG`/`$env:AUTH_DISABLED` (dotenv n'override pas
   l'env existant) ; pour un run permanent, fixer ces valeurs dans `server/.env`.
2. ◐ **protonesk** : build **déjà fait** (`dist/` + `node_modules/` présents).
   Reste (action user, interactif) : `hydroxide auth` (login Proton → bridge password),
   puis créer `proton-mail-bridge/.env` (`HYDROXIDE_USER`/`HYDROXIDE_PASSWORD` = bridge
   password). Vérifier ensuite `search_messages`.
3. ✅ **Ollama** : installé (0.30.8), `ollama serve` actif, `mistral:latest` présent
   → `score_job` opérationnel sans pull (embeddings `nomic-embed-text` aussi dispo en fallback).
4. ☐ **`.mcp.json` agent** : enregistrer les 3 serveurs (§10) avec la clé `mk_jobber_8e97…`.
   (Écriture bloquée auto — fichier de démarrage + secret ; à créer manuellement.)
5. ☐ **`pip install -r requirements.txt`** dans jobber (pour `mcp`, `beautifulsoup4`, etc.).
6. ☐ **Boucle bout-en-bout** (§5) sur un dossier réel : 1er run avec `SINCE` 7 jours,
   vérifier extraction → score → persistance → restitution triée.
7. ☐ **Nettoyer le seed de test** : supprimer les 2 jobs `TEST —` (`delete_by_id permanent`)
   une fois de vraies offres présentes.
8. ☐ **Ajuster** recettes IMAP + heuristiques company/location de l'extracteur sur
   de vrais emails (parsers par board si nécessaire).
9. ☐ **Cleanup legacy jobber** (pivot `NEXT.md`) : archiver `tailor.py`/`pdf_generator.py`/
   `apply_bot.py` dans `bmad/legacy/`, supprimer `tracker.py` + `jobber.db`, réécrire/retirer
   `main.py` (le store est idae, plus de SQLite).

« Fini » v1 : l'agent, à la demande, lit les nouvelles alertes, extrait, score,
dédup, persiste dans idae-machine et restitue un classement — par MCP, sans UI.

---

## 12. UI plus tard (idae-machine, hors v1)

Le modèle vit déjà dans idae-machine : quand le front sera prêt, les vues
Explorer/Card consomment `job`/`match_result`/`job_event` **sans migration** —
le store et le schéma sont les mêmes. Aucune dette : UNIFY n'écrit que des
données conformes à `jobberScheme`. (Composants UI non utilisés en v1, par
décision.)

---

## 13. Sécurité & PII

- **Clé API agent** : `mk_jobber_…` longue durée ; ne jamais committer. Révocable
  (`apikey_revoke`), résolue live (désactiver l'user tue la clé).
- **`MCP_SCHEMA_WRITE=false`** : interdit `schema_publish`/`seed_org` (destructif) via MCP.
- **`AUTH_DISABLED=false`** hors exploration : RBAC réel, audit (`appuser_audit`) de chaque appel.
- **PII CV** : `profile_parse(mask_pii=true)` par défaut.
- **Local-first** : mail via bridge local, scoring via Ollama local, Mongo local —
  aucune donnée d'offre ni de CV envoyée à un tiers par le pipeline.
- **Mots de passe bridge** ≠ mot de passe Proton.
- **Soft-delete** : `delete_by_id` marque `deletedAt` (réversible via `restore`) ;
  préférer `move_message` à `delete_message` côté mail.
```
