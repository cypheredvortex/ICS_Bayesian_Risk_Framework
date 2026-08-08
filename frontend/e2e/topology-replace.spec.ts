import { test, expect } from '@playwright/test'

// The file-replacement workflow must work entirely through normal React
// state — no page refresh — including replacing file A with B and then
// re-selecting A (the same file) again. Uploads use the real backend with
// example topologies from the repository's data directory.
test('topology file can be replaced and removed without a page refresh', async ({
  page,
}) => {
  await page.goto('/')

  const fileInput = page.locator('input[aria-label="Upload a topology file"]')
  const swatPath = '../data/swat_example.json'
  const substationPath = '../data/power_substation.json'

  // --- Initial state ---
  await expect(page.getByText(/No topology loaded yet/)).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Run assessment' }),
  ).toBeDisabled()

  // --- Upload A ---
  await fileInput.setInputFiles(swatPath)
  await expect(page.getByText(/Active topology:/)).toBeVisible()
  await expect(page.getByText('swat_example.json').first()).toBeVisible()
  await expect(page.getByText('Replace file')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Run assessment' })).toBeEnabled()

  // --- Replace A with B ---
  await page.getByRole('button', { name: 'Replace file' }).click()
  await fileInput.setInputFiles(substationPath)
  await expect(page.getByText('power_substation.json').first()).toBeVisible()
  await expect(page.getByText('swat_example.json')).toHaveCount(0)

  // --- Replace B with A again (same file re-selection) ---
  await page.getByRole('button', { name: 'Replace file' }).click()
  await fileInput.setInputFiles(swatPath)
  await expect(page.getByText('swat_example.json').first()).toBeVisible()

  // --- Remove returns to the empty state ---
  await page.getByRole('button', { name: 'Remove' }).click()
  await expect(page.getByText(/No topology loaded yet/)).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Run assessment' }),
  ).toBeDisabled()

  // --- No fatal console errors during the whole flow ---
  const errors: string[] = []
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text())
  })
  await page.reload()
  await expect(page.getByText('Topology & Assessment')).toBeVisible()
  expect(errors.filter((e) => !e.includes('favicon'))).toEqual([])
})
