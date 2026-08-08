import { test, expect } from '@playwright/test'

test('disclosure toggles and no horizontal overflow on narrow screens', async ({
  page,
}) => {
  await page.goto('/')

  // There are several collapsible sections on the dashboard now; scope each
  // locator to the disclosure it belongs to.
  const formatsDetails = page.locator('details.disclosure-no-marker', {
    hasText: 'Supported topology representations',
  })
  const evidenceDetails = page.locator('details.disclosure-no-marker', {
    hasText: 'Evidence Selection',
  })
  const summary = page.getByText('Supported topology representations')

  // --- Supported formats: collapsed by default, hidden content ---
  await expect(formatsDetails).not.toHaveAttribute('open')
  await expect(page.getByText('.vsdx / .vdx')).toBeHidden()

  // --- Click expands ---
  await summary.click()
  await expect(formatsDetails).toHaveAttribute('open')
  await expect(page.getByText('.vsdx / .vdx')).toBeVisible()
  await page.waitForTimeout(400) // let the panel animation settle

  // --- Click collapses ---
  await summary.click()
  await expect(formatsDetails).not.toHaveAttribute('open')
  await expect(page.getByText('.vsdx / .vdx')).toBeHidden()

  // --- Evidence Selection (embedded in Topology & Assessment): independent
  // disclosure state, collapsed by default, content hidden ---
  await expect(evidenceDetails).not.toHaveAttribute('open')
  await expect(page.getByLabel('Filter evidence assets')).toBeHidden()
  await page.getByText('Evidence Selection').click()
  await expect(evidenceDetails).toHaveAttribute('open')
  await expect(page.getByLabel('Filter evidence assets')).toBeVisible()
  await page.getByText('Evidence Selection').click()
  await expect(evidenceDetails).not.toHaveAttribute('open')

  // --- Bayesian Results (embedded in Network Viewer): collapsed by default,
  // content hidden ---
  const bayesianDetails = page.locator('details.disclosure-no-marker', {
    hasText: 'Bayesian Results',
  })
  await expect(bayesianDetails).not.toHaveAttribute('open')
  await expect(page.getByText('Run context and model outputs.')).toBeHidden()
  await page.getByText('Bayesian Results').click()
  await expect(bayesianDetails).toHaveAttribute('open')
  await expect(page.getByText('Run context and model outputs.')).toBeVisible()
  await page.getByText('Bayesian Results').click()
  await expect(bayesianDetails).not.toHaveAttribute('open')

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
