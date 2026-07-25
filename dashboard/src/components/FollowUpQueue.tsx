import type { JobApplication } from '../types';
import { computeDecay } from '../lib/decay';

export function FollowUpQueue({ apps }: { apps: JobApplication[] }) {
  const due = apps.filter((a) => computeDecay(a).isDue).sort((a, b) => computeDecay(b).level - computeDecay(a).level);

  if (due.length === 0) return null;

  return (
    <section className="panel follow-up">
      <h2>Needs attention ({due.length})</h2>
      <ul>
        {due.map((a) => {
          const d = computeDecay(a);
          return (
            <li key={a.id}>
              <strong>{a.title}</strong> at {a.company} &mdash; {d.label} ({d.daysSinceSignal}d silent)
            </li>
          );
        })}
      </ul>
    </section>
  );
}
