import { useState } from 'react';
import type { JobApplication, ApplicationStatus } from '../types';
import { computeDecay, reinforce } from '../lib/decay';
import * as api from '../lib/api';

const STATUS_FLOW: ApplicationStatus[] = [
  'new',
  'tailored',
  'applied',
  'replied',
  'interview',
  'rejected',
  'offer',
  'archived'
];

export function ApplicationCard({
  app,
  resume,
  onUpdate
}: {
  app: JobApplication;
  resume: unknown | null;
  onUpdate: (app: JobApplication) => void;
}) {
  const decay = computeDecay(app);
  const [busy, setBusy] = useState<string | null>(null);
  const [live, setLive] = useState(false);

  function addNote(text: string, status?: ApplicationStatus) {
    const reinforced = reinforce(app);
    onUpdate({
      ...reinforced,
      status: status ?? reinforced.status,
      notes: [{ at: new Date().toISOString(), text }, ...reinforced.notes]
    });
  }

  async function prepare() {
    if (!resume) return addNote('Prepare skipped: no resume uploaded yet.');
    setBusy('scoring');
    try {
      const jd = { title: app.title, company: app.company, description: app.jdText };
      const matchResult = await api.scoreJob(resume, jd);
      setBusy('tailoring');
      const tailoredResume = await api.tailorResume(resume, jd, matchResult);
      setBusy('rendering pdf');
      const { pdf_base64 } = await api.generatePdf(tailoredResume);
      onUpdate({
        ...reinforce(app),
        status: 'tailored',
        matchResult,
        tailoredResume,
        pdfBase64: pdf_base64,
        notes: [{ at: new Date().toISOString(), text: 'Tailored + scored via dashboard-api.' }, ...app.notes]
      });
    } catch (e) {
      addNote(`Prepare failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  }

  async function postuler() {
    if (!app.url) return addNote('Postuler skipped: no URL.');
    setBusy(live ? 'submitting (live)' : 'dry-run apply');
    try {
      const result = await api.apply(app.url, app.tailoredResume ?? resume, app.pdfBase64, live);
      addNote(
        live ? `Submitted live. ${JSON.stringify(result)}` : `Dry-run filled the form (no submit). ${JSON.stringify(result)}`,
        live ? 'applied' : app.status
      );
    } catch (e) {
      addNote(`Postuler failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <article className="app-row">
      <div className="app-row-main">
        <div className="app-row-title">
          <h3>{app.title}</h3>
          <span className="app-row-company">{app.company}</span>
        </div>
        <span className="app-row-meta">
          {decay.label} &middot; {decay.daysSinceSignal}d
        </span>
      </div>

      <div className="status-row">
        <select
          value={app.status}
          onChange={(e) => addNote(`Status -> ${e.target.value}`, e.target.value as ApplicationStatus)}
        >
          {STATUS_FLOW.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        {app.url && (
          <a href={app.url} target="_blank" rel="noreferrer">
            posting
          </a>
        )}
      </div>

      <div className="actions">
        <button className="btn" disabled={!!busy} onClick={prepare}>
          {busy && busy !== 'dry-run apply' && busy !== 'submitting (live)' ? busy + '…' : 'Prepare (score + tailor + PDF)'}
        </button>
        <label className="live-toggle">
          <input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} />
          live (actually submit)
        </label>
        <button className={live ? 'btn btn-danger' : 'btn'} disabled={!!busy} onClick={postuler}>
          {busy === 'dry-run apply' || busy === 'submitting (live)' ? busy + '…' : 'Postuler'}
        </button>
      </div>

      {app.notes.length > 0 && (
        <ul className="notes">
          {app.notes.slice(0, 4).map((n, i) => (
            <li key={i}>
              <time>{new Date(n.at).toLocaleDateString()}</time> {n.text}
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
