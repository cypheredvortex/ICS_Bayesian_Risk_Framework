import { test, expect } from '@playwright/test'
import path from 'node:path'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'

const specDir = path.dirname(fileURLToPath(import.meta.url))

// Visual QA: the Network Viewer must fit the whole topology on load (no
// manual scrolling), let the analyst zoom into a single zone, expose a
// fullscreen mode, and run without console errors.
const CHEMICAL_PLANT = path.join(
  specDir,
  '..',
  '..',
  'ics_topologies',
  'chemical_processing_plant',
  'chemical_processing_plant.json',
)

test('network viewer fits, zooms to zones and stays error-free', async ({ page }) => {
  test.skip(!fs.existsSync(CHEMICAL_PLANT), 'chemical plant topology not present')
  const consoleErrors: string[] = []
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text())
  })
  page.on('pageerror', (err) => consoleErrors.push(String(err)))

  await page.goto('/')
  await expect(page.getByText('Topology & Assessment')).toBeVisible()

  await page
    .locator('input[aria-label="Upload a topology file"]')
    .setInputFiles(CHEMICAL_PLANT)
  await expect(page.getByText('Architecture review')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByRole('button', { name: 'Run assessment' })).toBeEnabled()

  // The whole topology must be visible inside the canvas after the fit
  // animation (60 nodes + 8 zones for the chemical plant).
  await page.waitForTimeout(1500)
  const fit = await page.evaluate(() => {
    const canvasEl = document.querySelector('.network-canvas')
    const nodes = Array.from(
      document.querySelectorAll('.react-flow__node-network'),
    )
    if (!canvasEl) return { error: 'no canvas', nodeCount: nodes.length }
    const cr = canvasEl.getBoundingClientRect()
    const outside = nodes.filter((n) => {
      const r = n.getBoundingClientRect()
      return (
        r.right > cr.right + 2 ||
        r.left < cr.left - 2 ||
        r.bottom > cr.bottom + 2 ||
        r.top < cr.top - 2
      )
    }).length
    return { nodeCount: nodes.length, outsideCount: outside }
  })
  expect(fit.nodeCount).toBeGreaterThanOrEqual(60)
  expect(fit.outsideCount).toBeLessThanOrEqual(2)

  // Zone focus: clicking the Field zone chip zooms the viewport into it.
  const before = await page.evaluate(() => {
    const vp = document.querySelector('.react-flow__viewport') as HTMLElement
    return vp.style.transform
  })
  await page.getByRole('button', { name: /Field/ }).click()
  await page.waitForTimeout(900)
  const after = await page.evaluate(() => {
    const vp = document.querySelector('.react-flow__viewport') as HTMLElement
    return vp.style.transform
  })
  expect(after).not.toBe(before)

  // The legend names every relationship type and the edge-colour palette is
  // rendered. Edge labels are on by default, so the same type names also
  // appear on edges — .first() keeps the assertion on the legend entry.
  // (Post-assessment the legend is unchanged, so this can stay before the
  // run.)
  await expect(page.getByText('Relationship:', { exact: true })).toBeVisible()
  await expect(page.getByText('controls', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('monitors', { exact: true }).first()).toBeVisible()

  // Fullscreen toggle must exist and engage (headless Chromium supports the
  // Fullscreen API; when the browser blocks it we still require the control).
  // Exit via the same toggle (the real UX path) rather than Escape, which
  // headless Chromium does not always honour.
  const fullscreenButton = page.getByRole('button', { name: 'Fullscreen' })
  await expect(fullscreenButton).toBeVisible()
  await fullscreenButton.click()
  await expect
    .poll(() =>
      page.evaluate(() => Boolean(document.fullscreenElement)),
      { timeout: 5000 },
    )
    .toBe(true)
  // Two exit controls exist while fullscreen is active: the header toggle and
  // the in-canvas overlay (which keeps exit reachable inside the fullscreen
  // element). Click the overlay inside the canvas.
  await page
    .locator('.network-canvas button', { hasText: 'Exit fullscreen' })
    .click()
  await expect
    .poll(() =>
      page.evaluate(() => Boolean(document.fullscreenElement)),
      { timeout: 5000 },
    )
    .toBe(false)

  // Full workflow still runs and the page never overflows horizontally.
  // NB: "Results Dashboard" also appears in the empty-state card, so wait for
  // a stat that only exists in the real dashboard — the run on the chemical
  // plant takes a few seconds and the edges must carry weights before the
  // hover check below.
  await page.getByRole('button', { name: 'Run assessment' }).click()
  await expect(page.getByText('Overall Risk (worst case)')).toBeVisible({
    timeout: 60_000,
  })

  // Hovering an edge shows the detail chip (relationship, direction, causal
  // weight). Edge labels are on by default; the 'Edge labels' toggle hides
  // them. Done after the run so weights from the analysis are present. A
  // short horizontal edge has a zero-height bounding box (Playwright reports
  // it hidden), so hover an edge with real extent instead of the first in DOM
  // order.
  const edges = page.locator('.react-flow__edge')
  expect(await edges.count()).toBeGreaterThan(50)
  // Pick an edge whose *interaction path* (the invisible 20px-wide hit area
  // that actually receives the hover) has its centre inside the visible
  // canvas — not the edge group bbox, which the label pill inflates away
  // from the stroke. The viewport is still zoomed into the Field zone from
  // the earlier zone-focus step, so only edges whose hit area lies inside
  // the visible canvas can actually be hovered.
  const hoverableIndex = await page.evaluate(() => {
    const all = Array.from(document.querySelectorAll('.react-flow__edge'))
    const canvas = document
      .querySelector('.network-canvas')!
      .getBoundingClientRect()
    return all.findIndex((el) => {
      const path = el.querySelector('.react-flow__edge-interaction')
      if (!path) return false
      const r = path.getBoundingClientRect()
      const cx = r.left + r.width / 2
      const cy = r.top + r.height / 2
      return (
        r.width > 8 &&
        r.height > 8 &&
        cx > canvas.left &&
        cx < canvas.right &&
        cy > canvas.top &&
        cy < canvas.bottom
      )
    })
  })
  expect(hoverableIndex).toBeGreaterThanOrEqual(0)
  // The canvas can extend below the fold, so bring the edge into the
  // viewport first. force: on dense graphs, edges cross and React Flow's
  // invisible hit-area paths (react-flow__edge-interaction, stroke-width 20)
  // intercept the hover point of a neighbouring edge. The detail chip is
  // edge-agnostic, so we skip the interception check and still fire the real
  // mouse events.
  const edgeToHover = page
    .locator('.react-flow__edge-interaction')
    .nth(hoverableIndex)
  await edgeToHover.scrollIntoViewIfNeeded()
  await edgeToHover.hover({ force: true })
  await expect(page.getByRole('tooltip')).toBeVisible()
  await expect(page.getByText(/Causal weight/)).toBeVisible()
  await expect(page.getByText('→', { exact: true }).first()).toBeVisible()
  await page.mouse.move(2, 2)
  await expect(page.getByRole('tooltip')).toHaveCount(0)
  const labelsButton = page.getByRole('button', { name: 'Edge labels' })
  await expect(labelsButton).toHaveAttribute('aria-pressed', 'true')
  await labelsButton.click()
  await expect(labelsButton).toHaveAttribute('aria-pressed', 'false')

  const overflow = await page.evaluate(
    () =>
      document.documentElement.scrollWidth -
      document.documentElement.clientWidth,
  )
  expect(overflow).toBeLessThanOrEqual(0)

  expect(consoleErrors).toEqual([])
})
