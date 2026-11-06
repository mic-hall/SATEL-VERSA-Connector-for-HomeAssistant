# Publishing the prepared repository

The intended repository is `mic-hall/SATEL-VERSA-Connector-for-HomeAssistant`. URLs and codeowner are
already configured for that destination. If the owner changes, update manifest
URLs, codeowners, README links and this file before uploading.

## Upload only this project

The parent research workspace contains private credentials, captures, a DLOADX
installer and analysis output. **Do not publish the parent workspace.** This
folder is a separate, self-contained source tree; no Git repository has been
initialized here automatically. Use the generated source ZIP to move it into a
clean directory before `git init` or uploading through GitHub's web interface.
Do not run `git add .` from the parent workspace.

1. Run all checks in README.md and review TESTING.md for validation limits.
2. Run `python tools/build_release.py`. Extract the source ZIP into a new clean
   directory. Its `satel-versa-bridge/` directory is the repository root.
3. Create `satel-versa-bridge` on GitHub, with description:
   `Read-only SATEL VERSA input states for Home Assistant via ETHM-1 Plus`.
4. Upload/commit the clean source tree. Keep Issues and Actions enabled.
5. Set topics: `home-assistant`, `hacs`, `satel`, `versa`, `ethm-1-plus`.
6. Enable GitHub private vulnerability reporting when available.
7. Wait for the test/package and hassfest workflows. Review any failure before
   tagging a release; local tests do not substitute for remote validators.
8. Tag `v0.1.0-beta.2`, create a GitHub **prerelease**, and attach
   `satel_versa-0.1.0-beta.2.zip` and `SHA256SUMS`. The source ZIP is optional.
9. Users can then add the repository to HACS as a custom Integration repository.

HACS listing in the default store is a separate process; it is not claimed here.
Original generic icon assets are included in the integration’s `brand/` folder;
they do not reproduce SATEL’s logo. Review current default-store requirements
separately before applying for a listing. No GitHub repository, tag, commit or release is created by the local
release tool. GitHub Actions builds downloadable artifacts; it does not publish
releases automatically.

## Future releases

Update manifest version, diagnostics version, CHANGELOG.md and TESTING.md. Run
checks, build packages, review the archive contents, then create a matching tag
and release. Never include real connection settings or captured sessions as
fixtures. The release tool uses allowlists, not a recursive ZIP of the workspace.
