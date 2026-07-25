import { useQoolieCollection } from '@medyll/qoolie/react';
import { useJobberDb } from './lib/store';
import type { JobApplication } from './types';
import { AddApplicationForm } from './components/AddApplicationForm';
import { ApplicationCard } from './components/ApplicationCard';
import { FollowUpQueue } from './components/FollowUpQueue';
import { ResumeUpload } from './components/ResumeUpload';

const PROFILE_ID = 'me';

export default function App() {
  const db = useJobberDb();

  const {
    data: apps,
    loading: appsLoading,
    refresh: refreshApps
  } = useQoolieCollection<JobApplication[]>('applications', {
    query: (c) => c.getAll(),
    // qoolie's `reactive: true` subscribes to *sync* events and throws when
    // sync is disabled (which it is here, on purpose — this is a local-only
    // demo). We refresh manually after every mutation instead.
    reactive: false
  });

  const { data: profile, refresh: refreshProfile } = useQoolieCollection<{ id: string; resume: unknown } | null>(
    'profile',
    { query: (c) => c.get(PROFILE_ID), reactive: false }
  );

  if (appsLoading) return <p className="muted">opening local database…</p>;

  async function addApp(app: JobApplication) {
    await db.collection.applications.create(app);
    refreshApps();
  }

  async function updateApp(app: JobApplication) {
    await db.collection.applications.update(app.id, app);
    refreshApps();
  }

  async function saveResume(resume: unknown) {
    const existing = await db.collection.profile.get(PROFILE_ID);
    if (existing) await db.collection.profile.update(PROFILE_ID, { resume });
    else await db.collection.profile.create({ id: PROFILE_ID, resume });
    refreshProfile();
  }

  const list = apps ?? [];

  return (
    <main className="app">
      <h1>jobber dashboard</h1>
      <p className="tagline">
        Local-first job-hunt triage. Storage: qoolie/IndexedDB. Compute (score, tailor, PDF, apply): dashboard-api →
        jobber's Python engine. Nothing leaves your machine.
      </p>

      <ResumeUpload resume={profile?.resume ?? null} onParsed={saveResume} />

      <FollowUpQueue apps={list} />

      <AddApplicationForm onAdd={addApp} />

      <section className="app-list">
        <h2>Applications ({list.length})</h2>
        {list.map((app) => (
          <ApplicationCard key={app.id} app={app} resume={profile?.resume ?? null} onUpdate={updateApp} />
        ))}
      </section>
    </main>
  );
}
