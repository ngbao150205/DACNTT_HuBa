# Chromium sandbox for optional browser E2E tests

Only the disposable browser-test container uses this profile. The application
crawler uses curl_cffi and Docker's default seccomp profile.

Profile source: [Moby profiles, commit 6fe7deb1b9fb7c0397a4593480d7d22b9ee8caef](https://github.com/moby/profiles/blob/6fe7deb1b9fb7c0397a4593480d7d22b9ee8caef/seccomp/default.json).
Apache 2.0 license is preserved in MOBY-LICENSE. The namespace syscalls clone,
setns and unshare are additionally allowed for Chromium's sandbox, following
[Playwright Docker guidance](https://playwright.dev/python/docs/docker#crawling-and-scraping).
The test browser runs as UID 10001 with chromium_sandbox=True; no privileged,
SYS_ADMIN or seccomp-unconfined settings are used.
