import { test, expect } from '@playwright/test'

// Full browser workflow: upload topology -> validate -> run assessment ->
// inspect network & metrics -> apply evidence -> rerun -> verify posterior
// and risk changes -> export a report. Uploads the SWAT example topology
// from the repository's data directory.
test('full assessment workflow', async ({ page }) => {
  await page.goto('/')

  // --- Settings load from the backend ---
  // (exact match: the open panel adds a "Close Analysis Settings" button)
  const settingsButton = page.getByRole('button', {
    name: 'Settings',
    exact: true,
  })
  await settingsButton.click()
  // The logistic CVSS parameters must come from the backend, not hardcoded.
  await expect(page.getByLabel('Logistic slope k')).toBeVisible()
  await settingsButton.click() // close

  // --- Upload the SWAT example topology file ---
  await page.setInputFiles(
    'input[aria-label="Upload a topology file"]',
    '../data/swat_example.json',
  )
  await expect(page.getByText(/Active topology:/)).toBeVisible()
  // "N connections" only appears in the status bar — the upload toast says
  // "N relationships", so this assertion stays unambiguous.
  await expect(page.getByText(/\d+ connections/)).toBeVisible()

  // --- Run the assessment ---
  await page.getByRole('button', { name: 'Run assessment' }).click()
  await expect(
    page.getByText(/Assessment complete — results are now on the dashboard/),
  ).toBeVisible({ timeout: 60_000 })

  // --- Network is displayed with nodes ---
  await expect(page.getByText('Results Dashboard')).toBeVisible()
  await expect(page.getByText('Overall Risk (worst case)')).toBeVisible()

  // --- Select an asset and inspect its metrics ---
  await expect(page.getByText('Posterior probabilities')).toBeVisible()
  await expect(page.getByText('Risk Ranking by Asset')).toBeVisible()
  // Click the first asset row in the posterior list to select it in the
  // details panel. Scoped to the list: the Node Details panel also renders a
  // clickable asset-name button ("what is this asset?"), which would
  // otherwise match a bare /^plc_1/ locator first.
  const posteriorSection = page.locator('.stat-card', {
    hasText: 'Posterior probabilities',
  })
  await posteriorSection
    .getByRole('button', { name: /^plc_1/ })
    .first()
    .click()
  // Node details show intrinsic probability, posterior and risk index.
  // Some metric labels also appear in the Bayesian results panel, so scope
  // the assertions to the Node Details panel.
  const detailsPanel = page.locator('div.rounded-2xl', {
    hasText: 'Node Details',
  })
  await expect(detailsPanel.getByText('Intrinsic probability')).toBeVisible()
  await expect(detailsPanel.getByText('Consequence impact')).toBeVisible()
  await expect(
    detailsPanel.getByText('Risk index', { exact: true }),
  ).toBeVisible()

  // --- Capture a posterior value before applying evidence ---
  const posteriorBefore = await posteriorSection
    .getByRole('button', { name: /^plc_1/ })
    .first()
    .textContent()
  expect(posteriorBefore).toMatch(/\d\.\d{3}/)

  // --- Apply evidence and rerun ---
  // Evidence Selection lives inside the Topology & Assessment card as a
  // collapsible section (collapsed by default), so expand it first.
  await page.getByText('Evidence Selection').click()
  // NOTE: the completion toast of the first run may still be visible, so do
  // not key on it for the second run; poll the actual posterior value.
  await page
    .getByRole('button', { name: 'Mark plc_1 as Compromised' })
    .click()
  await page.getByRole('button', { name: 'Run assessment' }).click()

  // Evidence asset is shown as pinned/compromised in the dashboard
  await expect(page.getByText(/📌/).first()).toBeVisible({ timeout: 60_000 })

  // The posterior of the evidence-pinned asset must become 1.000 (pinned):
  // this polls until the rerun completes and proves the value CHANGED as a
  // direct consequence of the evidence + rerun.
  const posteriorButton = posteriorSection
    .getByRole('button', { name: /^plc_1/ })
    .first()
  await expect(posteriorButton).toContainText('1.000', { timeout: 60_000 })
  const posteriorAfter = await posteriorButton.textContent()
  expect(posteriorAfter).not.toEqual(posteriorBefore)

  // --- Export the risk register ---
  // Reports moved into the header control area next to Settings — open it
  // before using the export controls.
  await page
    .getByRole('button', { name: 'Reports', exact: true })
    .click()
  await expect(page.getByText('Risk register (CSV)')).toBeVisible()

  // --- Export the risk register (CSV) ---
  const downloadPromise = page.waitForEvent('download')
  await page.getByText('Download Risk register').click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toMatch(/\.csv$/i)

  // --- Export the full results record (JSON) ---
  await expect(page.getByText('Full results (JSON)')).toBeVisible()
  const jsonDownloadPromise = page.waitForEvent('download')
  await page.getByText('Download Full results').click()
  const jsonDownload = await jsonDownloadPromise
  expect(jsonDownload.suggestedFilename()).toMatch(/\.json$/i)

  // --- Export the assessment report (PDF) ---
  await expect(page.getByText('Assessment report (PDF)')).toBeVisible()
  const pdfDownloadPromise = page.waitForEvent('download')
  await page.getByText('Download Assessment report').click()
  const pdfDownload = await pdfDownloadPromise
  expect(pdfDownload.suggestedFilename()).toMatch(/\.pdf$/i)

  // --- No fatal console errors ---
  const errors: string[] = []
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text())
  })
  await page.reload()
  await expect(page.getByText('Topology & Assessment')).toBeVisible()
  expect(errors.filter((e) => !e.includes('favicon'))).toEqual([])
})
