---
name: imap-job-search
description: Methodology for AI-led email job search (UNIFY). Use when the user wants to find/triage job offers from their mailbox. Orchestrates the protonesk (mail), jobber (compute) and idae (store) MCP servers — search job-alert emails, extract postings, score fit vs profile, dedupe and persist to MongoDB, surface ranked matches. Triggers on "find jobs", "check job alerts", "run job search", "score new offers", "recherche d'emploi".
---

# imap-job-search

Non-code playbook for the UNIFY job-search loop. Three MCP servers, one store:
**protonesk** (mail I/O) → **jobber** (compute) → **idae** (MongoDB store,
`jobberScheme`). You are the orchestrator. Persist only data conforming to the
idae `job` / `match_result` / `job_skill` / `job_event` / `email_message`
collections. Never use idae UI components — MCP + DB only.

## Board map (sender domain → idae `job_source` + IMAP recipe)

| Source code | Sender domain | Typical FROM | Subject keywords | Shape |
|---|---|---|---|---|
| `linkedin` | linkedin.com | `jobs-noreply@linkedin.com`, `jobalerts-noreply@linkedin.com` | "jobs for you", "job alert", "new jobs" | digest (5-20) |
| `indeed` | indeed.com | `alert@indeed.com`, `donotreply@match.indeed.com` | "new jobs for", "recommended" | digest |
| `wttj` | welcometothejungle.com | `notifications@welcometothejungle.com` | "offres", "nouvelles offres" | digest |
| `glassdoor` | glassdoor.com | `noreply@glassdoor.com` | "job alert", "new jobs" | digest |
| `recruiter` | (varies) | personal recruiter mails | "opportunity", "poste", "role" | single |

`job_source` ids are seeded (linkedin=1, indeed=2, wttj=3, glassdoor=4,
recruiter=5, other=6).

## IMAP recipes (protonesk.search_messages)

- Resume point first: `idae.find_one(collection:"email_message", sort:{received_at:-1})` → use its `received_at` as `SINCE`.
- Per board: `FROM <sender domain> SINCE <date> [SUBJECT <keyword>]`.
- Default folder = INBOX; if the user files alerts into a label/folder, search there (`list_folders` to discover).
- Keep `SINCE` tight (last run, or 7 days on first run) — avoid re-scanning the whole mailbox.

## The loop

1. **Cursor** — last processed message date (find_one above).
2. **Search** — one `search_messages` per board with its recipe.
3. **Pre-filter** (cheap, before any LLM): skip messages already in idae
   (`find_one email_message {message_id}` with `processed:true`); skip obvious
   non-alerts by subject. Only then fetch bodies.
4. **Fetch** — `get_message` → HTML.
5. **Record message** — `idae.create {collection:"email_message", data:{code:message_id, message_id, sender, sender_domain, subject, received_at, job_source:<id>, processed:false}}`.
6. **Extract** — `jobber.extract_jobs_from_email(html, source_hint)` → postings.
7. **Per posting**: dedupe `find_one {collection:"job", query:{link}}`; if new, `jobber.score_job(profile, job)`.
8. **Persist** (FK targets before dependents, all writes use the `data` key):
   upsert `company` → `create job` (`data` with `job_status:1`=new, `job_source`,
   `company`, `email_message`, denormalized `score`/`gaps`) → `create match_result`
   (match_method:1=ollama) → `create job_skill` rows (skill_kind: matched=2 /
   missing=3) → `create job_event` (event_type:1, new_status:1).
9. **Close message** — `update_by_id {collection:"email_message", id, data:{processed:true, job_count:N}}`;
   optionally `protonesk.move_message` to a processed folder.
10. **Report** — `idae.find job {job_status:1} sort:{score:-1}` → summarize new
    matches (title @ company, score, top gaps, link). Let the user set status.

## Profile

Read once per run: `idae.find_one profile {active:true}`. Pull its skills
(`find profile_skill {profile:<id>}` → join `skill`) and pass the profile (with a
`skills` list of codes) to `score_job`. Re-parse only when the CV changes:
`jobber.profile_parse(resume_path)` then `idae.update_by_id {collection:"profile", id, data:{...}}`.

## Heuristics — what reaches the (slow) matcher

Pre-filter a posting OUT before `score_job` when, from title alone, it clearly
fails a hard constraint (wrong seniority floor, wrong location/remote policy,
wrong stack family). Everything plausible gets scored. Tune thresholds with the
user; default surface cut = `score >= 0.6`.

## Cadence & idempotency

- Re-run daily (or on user request). Never reprocess: dedupe is
  `email_message.message_id` (whole mail) + `job.link` (per posting).
- A digest re-sent by the board is skipped at step 3.
- The same posting seen across two boards dedupes on canonical `link`.

## Referential mapping (text → idae ids)

- `sender_domain` → `job_source` (table above).
- Title keywords → `seniority` (junior/mid/senior/lead/principal) and
  `contract_type` (cdi/cdd/freelance/internship/apprenticeship/temp) — set the FK
  when confident, else leave unset.
- `skills_detected` / matcher skills → `skill.code` via `skill.code`/`aliases`
  (`find skill` to resolve; create missing skills only if the user agrees).

## Don'ts

- Don't persist anything outside `jobberScheme` shapes.
- Don't hard-delete mail; prefer `move_message`. idae deletes are soft by default.
- Don't invent offers — real jobs come only from the mailbox. The two `TEST —`
  seeded jobs are safe to delete.
