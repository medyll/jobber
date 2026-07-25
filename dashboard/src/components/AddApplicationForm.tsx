import { useState } from 'react';
import type { JobApplication } from '../types';

export function AddApplicationForm({ onAdd }: { onAdd: (app: JobApplication) => void }) {
  const [title, setTitle] = useState('');
  const [company, setCompany] = useState('');
  const [url, setUrl] = useState('');
  const [jdText, setJdText] = useState('');

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title || !company) return;
    const now = new Date().toISOString();
    onAdd({
      id: crypto.randomUUID(),
      title,
      company,
      url,
      jdText,
      status: 'new',
      createdAt: now,
      lastSignalAt: now,
      notes: []
    });
    setTitle('');
    setCompany('');
    setUrl('');
    setJdText('');
  }

  return (
    <form className="panel add-form" onSubmit={submit}>
      <h2>Track a new application</h2>
      <div className="row">
        <input placeholder="Job title" value={title} onChange={(e) => setTitle(e.target.value)} required />
        <input placeholder="Company" value={company} onChange={(e) => setCompany(e.target.value)} required />
      </div>
      <input placeholder="Posting URL" value={url} onChange={(e) => setUrl(e.target.value)} />
      <textarea
        placeholder="Paste the job description here (used for scoring/tailoring)"
        value={jdText}
        onChange={(e) => setJdText(e.target.value)}
        rows={4}
      />
      <button type="submit" className="btn btn-primary">
        Add
      </button>
    </form>
  );
}
