// Stub for '@medyll/idae-idbql' — only used by @medyll/idae-sync's
// initSync(), which this app never calls (qoolie sync is disabled
// everywhere). See vendor/README.md.
export function getIdbqlEvent() {
  return {
    _adapters: null,
    _adapter: null,
    registerAdapters(adapters) {
      this._adapters = adapters;
    }
  };
}
