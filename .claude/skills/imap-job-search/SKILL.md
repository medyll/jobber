---
name: imap-job-search
description: Methodology for AI-led job search over the mailbox (UNIFY). Use when running or planning a jobber search loop — finding job-alert emails via the protonesk MCP, extracting postings via the jobber MCP, scoring fit, and persisting to the idae-machine store. Carries the non-code knowledge: per-board sender domains & subjects, IMAP query recipes, digest handling, cheap pre-filters, referential mapping (job_source/seniority/contract_type/skill), and re-run cadence / dedup. Triggers on "search jobs", "check job alerts", "run jobber", "new job matches", IMAP job recipes.
---

# imap-job-search

Methodology layer for the UNIFY job-search loop. **No executable code here** — it
orchestrates three MCP servers the agent already has:

- **`protonesk`** (proton-mail-bridge): mail I/O — `search_messages`, `get_message`,
  `list_messages`/`list_folders`, `mark_message`/`move_message`.
- **`jobber`** (compute, stateless): `extract_jobs_from_email(html, source_hint)`,
  `score_job(profile, job)`, `profile_parse(resume_path, mask_pii)`.
- **`idae`** (idae-machine store, MongoDB org=jobber): `find` / `find_one` / `get_by_id` /
  `count` / `aggregate` / `create` / `update_by_id` / `resolve_fks` / `health`.

Store is idae-machine. jobber never persists. Mail stays in Proton via the bridge.

---

## The loop (what the agent does)

1. **Cursor** — last processed message:
   `idae.find_one(collection:"email_message", sort:{received_at:-1})` → resume date.
2. **Discover** — `protonesk.search_messages` with a recipe below.
3. **Pre-filter** — drop noise (see heuristics) before any `get_message`/`score_job`.
4. **Dedup message** — `idae.find_one("email_message", {message_id})`; if present and
   `processed:true` → skip.
5. **Read** — `protonesk.get_message` → HTML.
6. **Trace message** — `idae.create("email_message", {code:message_id, message_id,
   sender, sender_domain, subject, received_at, job_source:<id>, processed:false})`.
7. **Extract** — `jobber.extract_jobs_from_email(html, source_hint)` → 1..N postings.
8. **Dedup posting** — `idae.find_one("job", {link})`; existing → skip.
9. **Score** — `jobber.score_job(profile, job)` (profile from step 0bis below).
10. **Persist** (FK order: targets before dependents) — `company` (find-or-create) →
    `job` → `match_result` → `job_skill`× → `job_event`(status_change→new).
11. **Close message** — `idae.update_by_id("email_message", id, {processed:true,
    job_count:N})`; optionally `protonesk.move_message` to a processed folder.
12. **Report** — `idae.find("job", {job_status:1}, sort:{score:-1}, limit)` → summarize
    top new matches; the user sets status.

**0bis — profile (once per session):**
`idae.find_one("profile", {active:true})`, pass it to every `score_job`. Re-parse the
CV only when it changes: `jobber.profile_parse(resume_path)` →
`idae.update_by_id("profile", 1, {...})`.

---

## Per-board sender domains & subjects

Keep current — boards change templates. `source_hint`/`job_source.code` in **bold**.

| Board | `source` | Sender domains (`FROM`) | Subject markers (`SUBJECT`) |
|---|---|---|---|
| LinkedIn | **linkedin** | `jobs-noreply@linkedin.com`, `jobalerts-noreply@linkedin.com`, `*@linkedin.com` | "job alert", "jobs for you", "X new jobs", "your job alert for" |
| Indeed | **indeed** | `alert@indeed.com`, `donotreply@indeed.com`, `invitetoapply@indeed.com` | "new jobs for", "jobs matching", "X new jobs" |
| Welcome to the Jungle | **wttj** | `*@welcometothejungle.com`, `jobs@welcometothejungle.com` | "offres", "nouvelles offres", "job suggestions" |
| Glassdoor | **glassdoor** | `noreply@glassdoor.com`, `jobs@glassdoor.com` | "new jobs", "job alert" |
| Recruiter (direct) | **recruiter** | personal/agency domains (no fixed list) | "opportunity", "poste", "opportunité", "role", reply-expected |

Inference: when `source_hint` is empty, jobber infers from posting links
(`SOURCE_BY_DOMAIN`). Pass a hint when known — recruiter mails have no board link.

---

## IMAP query recipes (protonesk.search_messages)

- **Per board since cursor**: `FROM jobs-noreply@linkedin.com SINCE <cursor>`
  (one search per board domain; combine with `SUBJECT` to tighten).
- **All alerts, recent**: `SINCE <cursor> SUBJECT "job"` — broad, needs pre-filter.
- **Targeted folder**: most alerts land in a label/folder ("Job alerts", "Updates",
  or Proton "Folders/Jobs"). `list_folders` → search within the right one to cut noise.
- **Recruiters**: harder. `SINCE <cursor>` in the primary inbox, then pre-filter on
  subject/body keywords; treat as `source:recruiter`, usually a single posting.

Notes: `SINCE` is date-granular (UTC midnight) — keep the cursor as a date and dedup
on `message_id` for same-day re-runs. Prefer narrow `FROM`+`SUBJECT` over broad `SINCE`
to save `get_message`/scoring cost.

---

## Digest vs single posting

- **Digests** (LinkedIn/Indeed/WTTJ/Glassdoor) bundle **5–20 postings** per mail →
  `extract_jobs_from_email` returns a list; loop dedup+score per item.
- **Recruiter** mails = usually **one** posting, often no clean board link. Extraction
  may yield 0 links → fall back: create the `job` from subject/body manually
  (`source:recruiter`, `link` = a stable synthetic key if none, e.g. `mailto:`+message_id).

---

## Cheap pre-filter (before the costly matcher)

Skip a message/posting before `score_job` when:
- `message_id` already `processed:true`, or `job.link` already exists.
- Subject is a non-job notification ("application viewed", "profile view",
  "X people searched", "connection", "newsletter").
- Posting title clearly off-target vs profile headline (wrong domain/seniority) —
  a keyword gate against `profile.skills` / headline before invoking Ollama.
- Location hard-fails a constraint (e.g. on-site in an excluded country) when the
  user has set one.

Server-side counts help triage cheaply:
`idae.count("job", {job_status:1})`, `idae.aggregate` grouped by `job_source` or score
window — summarize without pulling rows.

---

## Referential mapping (email → idae-machine ids)

Map extracted strings to seeded referentials (see `jobberScheme.ts` / `jobberSeed`):

- **`sender_domain` → `job_source.id`**: linkedin.com→1, indeed.com→2,
  welcometothejungle.com→3, glassdoor.com→4, recruiter→5, other→6.
- **title keywords → `seniority.id`**: "junior/jr"→1, "mid"→2, "senior/sr"→3,
  "lead/principal staff"→4, "principal/staff"→5.
- **title/body → `contract_type.id`**: "CDI"→1, "CDD"→2, "freelance/contract"→3,
  "internship/stage"→4, "apprenticeship/alternance"→5, "interim/temp"→6.
- **skills → `skill.code`**: normalize against `skill.code`/`skill.aliases`
  (resolve via `idae.find("skill")` once, cache). `job_skill.skill_kind`:
  required→1, matched→2, missing→3, detected→4.
- **`job_status` default** = `1` (new). Triage transitions create a `job_event`
  (`event_type:status_change`=1, `new_status:<id>`).

`score_job` returns `score` in **0..1** → write to `job.score` and
`match_result.score` as-is. `skills:[{code,kind}]` → one `job_skill` per entry.

---

## Cadence & dedup

- **When to re-run**: daily, or on user request. The cursor (latest
  `email_message.received_at`) bounds the `SINCE`.
- **Avoid reprocessing**: dedup on `email_message.message_id` (+ `processed`) and
  `job.link`. Same-day re-runs rely on `message_id`, not `SINCE`.
- **What to surface**: only new `job_status:1` rows, sorted by `score` desc; one-line
  per match (title @ company — score — top gap), then let the user set status.
- **Hygiene**: after processing, `protonesk.move_message` to a processed folder
  (reversible) rather than delete; never leave `email_message.processed:false` behind.

---

## Guardrails

- **PII**: `profile_parse(mask_pii=true)` by default; the scored profile needs skills
  and summary, not raw contact details.
- **Local-first**: mail via the local bridge, scoring via local Ollama, Mongo local —
  no posting/CV data leaves the machine through this loop.
- **No fake data**: never invent postings. Only persist what extraction produced. The
  two `TEST —` rows in the seed are deletable fixtures.
- **idae-machine auth**: agent uses `Bearer mk_jobber_…` (long-lived, revocable). `idae.health`
  to confirm `org:"jobber"` before writing.
