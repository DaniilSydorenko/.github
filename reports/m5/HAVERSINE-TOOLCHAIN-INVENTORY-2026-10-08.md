# M5-B Haversine Toolchain Inventory

Observed 2026-10-08 on `master` at `4316daf0d5b6b1fbe2b208e54ac6d80cfe9824f6`. Read-only inventory, not a compatibility/security certification.

## Verified CI
- `.github/workflows/ci.yml`: Node.js 22, `npm ci`, `xvfb-run --auto-servernum npm test`, `npm run build`; triggers on PR, master push and manual dispatch.
- CI run 37705358554 and Secret Scan 37705358578 succeeded on that master SHA. Neither proves PR #39's current head (`3808dbd5`) is green.

## Toolchain and package contract
- Package v1.6.0: 21 direct devDependencies, no declared runtime dependencies, `main: dist/build.js`; no declared `types`, `exports` or `engines`.
- TypeScript ^4.4.4, Webpack ^5.64.0, Babel 7, Karma ^6.3.8, Jasmine ^3.10.1, Chrome launcher; package-lock version 2.
- TypeScript targets ES6/CommonJS; Webpack emits UMD `dist/build.js` and a source map. The bundle exists in the repository.
- Babel config targets browser defaults and IE >= 11, but this is not proof of browser compatibility.
- `.npmignore` does not explicitly exclude `src`, `spec` or `docs`; actual npm tarball contents are unverified.

## Open evidence gaps
1. Run `npm ls --all` and `npm audit --json` to classify direct/transitive dependency issues.
2. Run `npm pack --dry-run --json`; verify package entry point, tarball contents and declarations.
3. Test actual Node/CommonJS and browser/UMD consumers and define a supported matrix.
4. Review Karma/Jasmine modernization separately; no blind dependency upgrades.
5. Recheck draft PR #39's synchronization and exact-head CI independently.

No consumer writes, publication, release, or visibility changes authorized.
