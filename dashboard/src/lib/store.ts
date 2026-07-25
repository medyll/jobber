// qoolie collection setup — local-first storage, no server dependency.
// Sync is left disabled: this is a standalone demo, not wired to
// idae-machine's store (see project notes on why).
import { useQoolie } from '@medyll/qoolie/react';
import type { CollectionConfigMap } from '@medyll/qoolie';

export const collections = {
  applications: { keyPath: 'id' },
  profile: { keyPath: 'id' }
} satisfies CollectionConfigMap;

export function useJobberDb() {
  return useQoolie({
    dbName: 'jobber-dashboard',
    sync: false,
    collections
  });
}
