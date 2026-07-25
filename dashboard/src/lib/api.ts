// Thin client for dashboard-api (../dashboard-api/main.py). Stateless calls
// only — nothing here persists anything, storage is qoolie (see store.ts).
const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8420';

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status} ${await res.text()}`);
  return res.json();
}

export async function parseResume(file: File, maskPii = true) {
  const form = new FormData();
  form.append('file', file);
  form.append('mask_pii', String(maskPii));
  const res = await fetch(`${BASE}/parse-resume`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`parse-resume failed: ${res.status} ${await res.text()}`);
  return res.json();
}

export function scoreJob(resume: unknown, jd: unknown) {
  return post<Record<string, unknown>>('/score', { resume, jd });
}

export function tailorResume(resume: unknown, jd: unknown, matchResult: unknown) {
  return post<Record<string, unknown>>('/tailor', { resume, jd, match_result: matchResult });
}

export function generatePdf(resume: unknown) {
  return post<{ pdf_base64: string }>('/pdf', { resume });
}

/** dry-run by default — the caller must pass live:true explicitly to actually submit. */
export function apply(url: string, resume: unknown, pdfBase64: string | undefined, live = false) {
  return post<Record<string, unknown>>('/apply', { url, resume, pdf_base64: pdfBase64, live });
}
