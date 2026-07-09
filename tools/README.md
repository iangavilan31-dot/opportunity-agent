# tools/

## google_maps_scraper.exe (gitignored — download on fresh clone)

Free MIT-licensed Google Maps scraper (gosom/google-maps-scraper), the primary
lead source for the morning autopilot (`backend/source_maps.py`).

```powershell
# v1.16.1, windows-amd64 (any newer release works too):
curl -L -o tools/google_maps_scraper.exe https://github.com/gosom/google-maps-scraper/releases/download/v1.16.1/google_maps_scraper-1.16.1-windows-amd64.exe
```

## Playwright driver gotcha (fixed 2026-07-08)

The binary embeds playwright-go, which tries to download its driver from
`playwright.azureedge.net` — a CDN Microsoft retired (404s), and the successor
driver path 400s too ([playwright#38273](https://github.com/microsoft/playwright/issues/38273)).
Fix applied on this machine: the driver directory was assembled manually at
`%LOCALAPPDATA%\ms-playwright-go\1.57.0\` as

- `node.exe` — copy of the system Node
- `package\` — the `playwright-core@1.57.0` npm package (dependency-free)

Verify with: `node.exe package\cli.js --version` → `Version 1.57.0`.
If a future scraper release bumps its playwright version, repeat with the new
version number (`npm install playwright-core@<ver>`, copy into
`ms-playwright-go\<ver>\package`).
