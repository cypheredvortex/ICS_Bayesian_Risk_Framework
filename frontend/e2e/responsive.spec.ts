import { test, expect } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const specDir = path.dirname(fileURLToPath(import.meta.url))
const CHEMICAL_PLANT = path.join(specDir, '..', '..', 'ics_topologies', 'chemical_processing_plant', 'chemical_processing_plant.json')

/**
 * Responsive / layout QA at laptop resolutions.
 *
 * Guards the analyst-facing layout: no horizontal page overflow, the
 * uploaded topology's summary and zone chips render correctly, and the
 * Network Viewer fits the whole graph without page-level scrollbars.
 */
for (const viewport of [
  { name: 'laptop-1366', width: 1366, height: 768 },
  { name: 'small-laptop-1280', width: 1280, height: 720 },
]) {
  test(`no overflow and topology fits at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    await page.goto('/')

    await page.locator('input[aria-label="Upload a topology file"]').setInputFiles(CHEMICAL_PLANT)
    await page.getByText('Architecture review').waitFor({ timeout: 30000 })

    // The upload really parsed the chemical plant (60 assets, 8 zones, 81 links).
    await expect(page.getByText('60', { exact: true }).first()).toBeVisible()
    await expect(page.getByText('81', { exact: true }).first()).toBeVisible()

    // No horizontal page overflow at this width.
    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }))
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1)

    // Zone chips from the parsed topology are present (proves zones parsed).
    await expect(page.getByRole('button', { name: /Field/ }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: /IDMZ/ }).first()).toBeVisible()

    // Network Viewer canvas fits the graph: every rendered node lies inside
    // the canvas element and the page itself has no extra scrollbars.
    const fit = await page.evaluate(() => {
      const canvas = document.querySelector('.network-canvas') as HTMLElement | null
      if (!canvas) return { ok: false, reason: 'no canvas' }
      const cr = canvas.getBoundingClientRect()
      const nodes = Array.from(document.querySelectorAll('.react-flow__node-network')) as HTMLElement[]
      if (nodes.length === 0) return { ok: false, reason: 'no nodes' }
      const outside = nodes.filter((n) => {
        const r = n.getBoundingClientRect()
        return r.left < cr.left || r.right > cr.right || r.top < cr.top || r.bottom > cr.bottom
      }).length
      return { ok: outside === 0, outside, total: nodes.length }
    })
    expect(fit.ok, JSON.stringify(fit)).toBe(true)

    // Selecting an asset must not break the layout.
    await page.locator('.react-flow__node-network').first().click()
    await page.getByText('Asset identity').first().waitFor({ timeout: 10000 })
  })
}
