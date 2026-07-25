// Stub for '@medyll/idae-api/client' — this dashboard never enables qoolie
// sync (sync: false everywhere), so idae-sync's server-first path that
// depends on this client is dead code. It exists only so the static
// `import { IdaeApiClient } from '@medyll/idae-api/client'` in
// @medyll/idae-sync resolves at build time. See vendor/README.md.
export class IdaeApiClient {
  static getInstance() {
    throw new Error('IdaeApiClient stub: sync is disabled in this app, this path should never run.');
  }
}
