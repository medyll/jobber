import { useState } from 'react';
import * as api from '../lib/api';

export function ResumeUpload({
  resume,
  onParsed
}: {
  resume: unknown | null;
  onParsed: (resume: unknown) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setBusy(true);
    setError(null);
    try {
      onParsed(await api.parseResume(file));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel resume-upload">
      <h2>Resume</h2>
      {resume ? (
        <p className="ok">Resume parsed and ready — reused for every "Prepare".</p>
      ) : (
        <p className="muted">Upload once, reused for scoring/tailoring across all applications.</p>
      )}
      <input
        type="file"
        accept=".pdf,.docx"
        disabled={busy}
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      {busy && <span> parsing…</span>}
      {error && <p className="error">dashboard-api unreachable: {error}</p>}
    </section>
  );
}
