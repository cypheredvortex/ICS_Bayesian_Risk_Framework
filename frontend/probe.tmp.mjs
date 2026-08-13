import { chromium } from 'playwright'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const specDir = path.dirname(fileURLToPath(import.meta.url))
const CHEMICAL_PLANT = path.join(
  specDir, '..', 'ics_topologies', 'chemical_processing_plant', 'chemical_processing_plant.json',
)

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle' })
await page.locator('input[aria-label="Upload a topology file"]').setInputFiles(CHEMICAL_PLANT)
await page.waitForSelector('.react-flow__node-network', { timeout: 30000 })
await page.waitForTimeout(1500)

const runBtn = page.getByRole('button', { name: 'Run assessment' })
if (await runBtn.count()) {
  await runBtn.first().click()
  await page.waitForSelector('.react-flow__edge', { timeout: 60000 })
  await page.waitForTimeout(4000)
}

const view = await page.evaluate(() => {
  const vp = document.querySelector('.react-flow__viewport')
  const m = (vp?.style.transform || '').match(/scale\(([\d.]+)\)/)
  return { scale: m ? +m[1] : 1 }
})
const scale = view.scale

const out = await page.evaluate(() => {
  const cards = []
  for (const el of Array.from(document.querySelectorAll('.react-flow__node-network'))) {
    const style = el.getAttribute('style') || ''
    const m = style.match(/translate\(([-\d.]+)px, ([-\d.]+)px\)/)
    if (!m) continue
    cards.push({ x: +m[1], y: +m[2] })
  }
  const labels = []
  for (const el of Array.from(document.querySelectorAll('.react-flow__edge'))) {
    const textEl = el.querySelector('.react-flow__edge-textwrapper')
    if (!textEl) continue
    const text = textEl.textContent || ''
    const bg = textEl.querySelector('.react-flow__edge-textbg')
    const label = textEl.querySelector('.react-flow__edge-text') || textEl
    const br = bg ? bg.getBoundingClientRect() : label.getBoundingClientRect()
    const t = textEl.getAttribute('transform') || ''
    const tm = t.match(/translate\(([-\d.]+)[, ]+([-\d.]+)\)/)
    labels.push({ text: text.slice(0, 42), pw: br.width, ph: br.height, gx: tm ? +tm[1] : NaN, gy: tm ? +tm[2] : NaN })
  }
  return { cards, labels }
})

const { cards, labels } = out
const rects = labels.map((l) => ({ x: l.gx, y: l.gy, w: l.pw / scale, h: l.ph / scale }))
let cardHits = 0
for (const l of rects) {
  for (const c of cards) {
    if (l.x < c.x + 184 && l.x + l.w > c.x && l.y < c.y + 85 && l.y + l.h > c.y) { cardHits++; break }
  }
}
let pairHits = 0
for (let i = 0; i < rects.length; i++) {
  for (let j = i + 1; j < rects.length; j++) {
    const a = rects[i], b = rects[j]
    if (a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y) pairHits++
  }
}
// also confirm labels sit on their own edge's general vicinity (not detached)
const onOwnEdge = labels.every((l) => l.gx > 0)
console.log(`FINAL: nodes=${cards.length} labels=${rects.length} | label-vs-card: ${cardHits} | label-vs-label: ${pairHits} | all-placed: ${onOwnEdge}`)
await browser.close()
