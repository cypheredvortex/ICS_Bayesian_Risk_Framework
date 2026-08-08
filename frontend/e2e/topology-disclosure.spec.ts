import { test, expect } from '@playwright/test'

test('disclosure toggles and no horizontal overflow on narrow screens', async ({
  page,
}) => {
  await page.goto('/')

  const details = page.locator('details.disclosure-no-marker')
  const summary = page.getByText('Supported topology representations')

  // --- Collapsed by default: no open attribute, format content hidden ---
  await expect(details).not.toHaveAttribute('open')
  await expect(page.getByText('.vsdx / .vdx')).toBeHidden()

  // --- Click expands ---
  await summary.click()
  await expect(details).toHaveAttribute('open')
  await expect(page.getByText('.vsdx / .vdx')).toBeVisible()
  await page.waitForTimeout(400) // let the panel animation settle

  // --- Click collapses ---
  await summary.click()
  await expect(details).not.toHaveAttribute('open')
  await expect(page.getByText('.vsdx / .vdx')).toBeHidden()

  // --- Narrow viewport: no horizontal overflow, key controls visible ---
  await page.setViewportSize({ width: 390, height: 844 })
  await page.reload()
  await expect(page.getByText('Topology & Assessment')).toBeVisible()
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow).toBeLessThanOrEqual(0)
  await expect(page.getByText(/Drag & drop a topology file/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Run assessment' })).toBeVisible()
  await expect(page.getByText('Sample topology')).toBeVisible()
})
