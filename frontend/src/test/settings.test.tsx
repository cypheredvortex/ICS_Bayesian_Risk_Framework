import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// Range inputs cannot be typed/cleared like text fields; setting the value
// through a change event is the reliable way to drive them in tests.
function setSlider(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), {
    target: { value },
  })
}

import App from '../App'
import { defaultSettingsPayload, installFetchMock } from './helpers'

async function openSettings(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: /Settings/ }))
}

function routes() {
  return installFetchMock([
    {
      url: '/settings',
      method: 'GET',
      json: { ...defaultSettingsPayload, cvss_logistic_params: { k: 1.2, x0: 4.5 } },
    },
    {
      url: '/settings',
      method: 'PUT',
      json: { ...defaultSettingsPayload, cvss_logistic_params: { k: 1.2, x0: 4.5 } },
    },
    { url: '/settings/reset', method: 'POST', json: defaultSettingsPayload },
  ])
}

describe('Settings', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('loads settings from the backend and exposes CVSS parameters', async () => {
    const restore = routes()
    const user = userEvent.setup()
    render(<App />)
    await openSettings(user)
    // The k slider should carry the server-provided value 1.2.
    const kSlider = await screen.findByLabelText('Logistic slope k')
    expect(kSlider).toHaveValue('1.2')
    expect(screen.getByLabelText('CVSS to probability mapping method')).toHaveValue(
      'logistic',
    )
    restore()
  })

  it('exposes the active risk thresholds from the backend', async () => {
    const restore = routes()
    const user = userEvent.setup()
    render(<App />)
    await openSettings(user)
    const critical = await screen.findByLabelText('Critical risk threshold')
    expect(critical).toHaveValue('0.75')
    expect(screen.getByLabelText('High risk threshold')).toHaveValue('0.5')
    expect(screen.getByLabelText('Moderate risk threshold')).toHaveValue('0.25')
    restore()
  })

  it('marks settings dirty when a threshold changes', async () => {
    const restore = routes()
    const user = userEvent.setup()
    render(<App />)
    await openSettings(user)
    await screen.findByLabelText('Critical risk threshold')
    setSlider('Critical risk threshold', '0.8')
    expect(screen.getByText(/Settings •/)).toBeInTheDocument()
    restore()
  })

  it('saves settings through PUT /settings', async () => {
    const putHandler = vi.fn()
    const restore = installFetchMock([
      { url: '/settings', method: 'GET', json: defaultSettingsPayload },
      {
        url: '/settings',
        method: 'PUT',
        handler: (init) => {
          putHandler(init)
          return { status: 200, json: defaultSettingsPayload }
        },
      },
    ])
    const user = userEvent.setup()
    render(<App />)
    await openSettings(user)
    // Make a change so the Save button becomes enabled.
    await screen.findByLabelText('Logistic slope k')
    setSlider('Logistic slope k', '1.5')
    await user.click(screen.getByRole('button', { name: /Save changes/ }))
    await waitFor(() => expect(putHandler).toHaveBeenCalledTimes(1))
    expect(
      await screen.findByText(
        'Settings saved. They apply to the next assessment you run.',
      ),
    ).toBeInTheDocument()
    restore()
  })

  it('surfaces a backend validation error when the configuration is invalid', async () => {
    const restore = installFetchMock([
      { url: '/settings', method: 'GET', json: defaultSettingsPayload },
      {
        url: '/settings',
        method: 'PUT',
        handler: () => ({
          status: 400,
          json: { detail: "'risk_thresholds' must satisfy: critical > high > moderate." },
        }),
      },
    ])
    const user = userEvent.setup()
    render(<App />)
    await openSettings(user)
    await screen.findByLabelText('Logistic slope k')
    setSlider('Logistic slope k', '1.5')
    await user.click(screen.getByRole('button', { name: /Save changes/ }))
    // Match the full backend detail string (the settings panel also mentions
    // the ordering constraint, so match something unique to the toast).
    expect(
      await screen.findByText(/'risk_thresholds' must satisfy: critical > high > moderate/),
    ).toBeInTheDocument()
    restore()
  })

  it('resets settings to defaults via the reset endpoint', async () => {
    const resetHandler = vi.fn()
    const restore = installFetchMock([
      {
        url: '/settings',
        method: 'GET',
        json: { ...defaultSettingsPayload, cvss_logistic_params: { k: 1.2, x0: 4.5 } },
      },
      { url: '/settings', method: 'PUT', json: defaultSettingsPayload },
      {
        url: '/settings/reset',
        method: 'POST',
        handler: () => {
          resetHandler()
          return { status: 200, json: defaultSettingsPayload }
        },
      },
    ])
    const user = userEvent.setup()
    render(<App />)
    await openSettings(user)
    await screen.findByLabelText('Logistic slope k')
    await user.click(screen.getByRole('button', { name: 'Reset to defaults' }))
    await waitFor(() => expect(resetHandler).toHaveBeenCalledTimes(1))
    expect(
      await screen.findByText('Settings reset to framework defaults.'),
    ).toBeInTheDocument()
    restore()
  })
})
