# vendor/

qoolie is an unpublished workspace package inside the idae monorepo, and its
runtime dependency `@medyll/idae-sync` is unpublished too. This dashboard
lives in a separate repo/pnpm scope, so it can't resolve `workspace:*`.

These `.tgz` are `pnpm pack` output from idae's packages, with unused
transitive `@medyll/*` deps (CLI-only, unimported at runtime) stripped from
each tarball's `package.json` so install doesn't try to fetch unpublished
packages that aren't actually needed here.

Regenerate after updating qoolie:

```bash
cd D:/development/idae/packages/qoolie && pnpm pack --pack-destination D:/development/jobber/dashboard/vendor
cd D:/development/idae/packages/idae-sync && pnpm pack --pack-destination D:/development/jobber/dashboard/vendor
cd D:/development/idae/packages/skiller && pnpm pack --pack-destination D:/development/jobber/dashboard/vendor
# then strip @medyll/skiller from qoolie's package.json inside the tgz,
# and @medyll/idae-idbql + @medyll/idae-api from idae-sync's — see git history
# of this file for the exact patch, or just remove any dependency that isn't
# statically imported by dist/index.js / dist/react/*.js.
```
