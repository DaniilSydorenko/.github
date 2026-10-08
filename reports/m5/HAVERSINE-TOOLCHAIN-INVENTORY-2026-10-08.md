# M5-B Haversine Toolchain Inventory

Observed 2026-10-08 on master 4316daf0.

CI runs Node.js 22, npm ci, Karma/Jasmine tests under Xvfb, and Webpack build. CI run 37705358554 and Secret Scan 37705358578 both succeeded on 4316daf0.

Package 1.6.0 declares no runtime dependencies and 21 devDependencies, including TypeScript 4.4, Webpack 5, Babel 7, Karma 6 and Jasmine 3. Browser/Node compatibility beyond CI and transitive advisories remain unverified.

Next: npm ls --all, npm audit --json, npm pack --dry-run, consumer import tests, explicit support matrix. PR #39 requires independent exact-head CI. No consumer changes authorized.
