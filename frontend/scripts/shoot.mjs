// Web Machine QA — REAL interactions in a VISIBLE browser (law: no
// dispatchEvent, no hidden tabs — hidden tabs freeze rAF for WebGL/canvas).
// Usage: node scripts/shoot.mjs
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const outDir = join(root, 'docs', 'shots')
mkdirSync(outDir, { recursive: true })

const BASE = 'http://localhost:5120'
const report = { consoleErrors: [], pageErrors: [], fps: {}, notes: [] }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const browser = await chromium.launch({
  headless: false,
  args: ['--window-position=40,40', '--window-size=1650,1040'],
})
const page = await browser.newPage({ viewport: { width: 1600, height: 950 } })
page.on('console', (m) => {
  if (m.type() === 'error') report.consoleErrors.push(m.text().slice(0, 300))
})
page.on('pageerror', (e) => report.pageErrors.push(String(e).slice(0, 300)))

async function shot(name) {
  await page.screenshot({ path: join(outDir, name + '.png') })
  console.log('shot:', name)
}
async function fps(label, ms = 2000) {
  const n = await page.evaluate(
    (dur) =>
      new Promise((res) => {
        let c = 0
        const t0 = performance.now()
        const tick = () => {
          c++
          if (performance.now() - t0 < dur) requestAnimationFrame(tick)
          else res(c)
        }
        requestAnimationFrame(tick)
      }),
    ms,
  )
  report.fps[label] = Math.round((n / ms) * 1000)
  console.log('fps', label, report.fps[label])
}

// ── 1. THE FIELD ──────────────────────────────────────────────────────────
await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
await sleep(4500) // data + fonts + camera settle
await shot('01-field')
await fps('field')

// hover the Sent ledger row — real mouse, real hit-testing
const sentRow = page.locator('span:text-is("Reached")').first()
await sentRow.hover({ timeout: 5000 }).catch((e) => report.notes.push('ledger hover failed: ' + e.message))
await sleep(1400)
await shot('02-field-focus-sent')

// sweep the cursor across the field until a single business card appears
let foundTip = false
outer: for (let gx = 0.3; gx <= 0.75; gx += 0.045) {
  for (let gy = 0.25; gy <= 0.75; gy += 0.06) {
    await page.mouse.move(1600 * gx, 950 * gy, { steps: 2 })
    await sleep(60)
    if (await page.locator('div.emerge').count()) { foundTip = true; break outer }
  }
}
report.notes.push('business card on node hover: ' + (foundTip ? 'OK' : 'NOT FOUND'))
if (foundTip) await shot('03-field-business-card')

// real click on empty space clears / locks focus without crashing
await page.mouse.click(800, 200)
await sleep(400)

// ── 2. GROWTH ATLAS (rail click — real navigation) ───────────────────────
await page.locator('a[title="Atlas"]').click()
await sleep(2500)
await shot('04-atlas-live')
await fps('atlas')

// drag the timeline to ~35% — real pointer drag
const track = page.locator('div.cursor-ew-resize')
const tb = await track.boundingBox()
if (tb) {
  await page.mouse.move(tb.x + tb.width * 0.98, tb.y + tb.height / 2)
  await page.mouse.down()
  await page.mouse.move(tb.x + tb.width * 0.35, tb.y + tb.height / 2, { steps: 12 })
  await page.mouse.up()
  await sleep(700)
  await shot('05-atlas-scrubbed')
} else {
  report.notes.push('timeline track NOT FOUND')
}

// press play, let the network re-grow
await page.locator('button[title*="Replay"]').click().catch(() => report.notes.push('play button missing'))
await sleep(4000)
await shot('06-atlas-replaying')
await page.locator('button:text-is("Live")').click().catch(() => {})
await sleep(600)

// hover a Phoenix-cluster business (real position sweep near the southwest)
let mapTip = false
mapouter: for (let gx = 0.18; gx <= 0.4; gx += 0.02) {
  for (let gy = 0.5; gy <= 0.75; gy += 0.03) {
    await page.mouse.move(1600 * gx, 950 * gy, { steps: 2 })
    await sleep(50)
    if (await page.locator('div.emerge').count()) { mapTip = true; break mapouter }
  }
}
report.notes.push('atlas business card: ' + (mapTip ? 'OK' : 'NOT FOUND'))
if (mapTip) await shot('07-atlas-business-card')

// ── 3. WORKFLOW SURFACES ──────────────────────────────────────────────────
const pages = [
  ['Overview', '08-overview'],
  ['Queue', '09-queue'],
  ['Send', '10-send'],
  ['Follow up', '11-followups'],
  ['Outreach', '12-outreach'],
  ['Analytics', '13-analytics'],
  ['Pipeline', '14-pipeline'],
  ['Settings', '15-settings'],
]
for (const [title, name] of pages) {
  await page.locator(`a[title="${title}"]`).click()
  await sleep(1200)
  await shot(name)
}

// back home for the record
await page.locator('a[title="Field"]').click()
await sleep(1500)

writeFileSync(join(outDir, 'qa-report.json'), JSON.stringify(report, null, 2))
console.log(JSON.stringify(report, null, 2))
await browser.close()
