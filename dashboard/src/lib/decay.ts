// Decay model ported from humemory's 5-level trace decay: an application
// that gets no new signal (reply, status change, note) decays through
// stages, and resurfaces in the follow-up queue before you'd think to check
// it yourself. Any real signal reinforces the trace back to level 0.
import type { JobApplication } from '../types';

export const DECAY_THRESHOLDS_DAYS = [3, 7, 14, 30] as const;

export const DECAY_LABELS = [
  'fresh',
  'check in',
  'ping recruiter',
  'going cold',
  'stale — decide: archive or last shot'
] as const;

export interface DecayInfo {
  level: 0 | 1 | 2 | 3 | 4;
  label: (typeof DECAY_LABELS)[number];
  daysSinceSignal: number;
  isDue: boolean;
}

const DAY_MS = 24 * 60 * 60 * 1000;

export function computeDecay(app: JobApplication, now: Date = new Date()): DecayInfo {
  const daysSinceSignal = Math.floor((now.getTime() - new Date(app.lastSignalAt).getTime()) / DAY_MS);

  let level: DecayInfo['level'] = 0;
  for (let i = 0; i < DECAY_THRESHOLDS_DAYS.length; i++) {
    if (daysSinceSignal >= DECAY_THRESHOLDS_DAYS[i]) level = (i + 1) as DecayInfo['level'];
  }

  const terminal = app.status === 'rejected' || app.status === 'offer' || app.status === 'archived';

  return {
    level,
    label: DECAY_LABELS[level],
    daysSinceSignal,
    isDue: !terminal && level >= 1
  };
}

/** Reinforcement: any real signal resets decay to 0, like a recall event in humemory. */
export function reinforce(app: JobApplication, now: Date = new Date()): JobApplication {
  return { ...app, lastSignalAt: now.toISOString() };
}

export function sortByUrgency(apps: JobApplication[], now: Date = new Date()): JobApplication[] {
  return [...apps].sort((a, b) => computeDecay(b, now).level - computeDecay(a, now).level);
}
