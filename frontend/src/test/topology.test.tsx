import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import App from '../App'
import { defaultSettingsPayload, installFetchMock, smallTopology } from './helpers'
import type { TopologyPayload } from '../types'

describe('Topology upload', () => {
  it('accepts a valid JSON topology file and reports the counts', async () => {
    const user = userEvent.setup()
    const restore = installFetchMock([
      { url: '/settings', method: 'GET', json: defaultSettingsPayload },
      {
        url: '/upload-topology-file',
        method: 'POST',
        json: { asset_count: 1, relationship_count: 0, topology: smallTopology },
      },
    ])
    render(<App />)
    const input = await screen.findByLabelText('Upload a topology file')
    const file = new File([JSON.stringify(smallTopology)], 'my_topology.json', {
      type: 'application/json',
    })
    await user.upload(input, file)
    expect(
      await screen.findByText(/Loaded my_topology.json: 1 assets, 0 relationships/),
    ).toBeInTheDocument()
    // "Active topology:" is a label followed by a <strong> filename; check
    // both parts since the text is split across nested elements. The
    // filename also appears in the review panel, so match any occurrence.
    expect(screen.getByText(/Active topology:/)).toBeInTheDocument()
    expect(screen.getAllByText('my_topology.json').length).toBeGreaterThan(0)
    restore()
  })

  it('rejects an unsupported extension without calling the backend', async () => {
    const user = userEvent.setup()
    let uploadCalled = false
    const restore = installFetchMock([
      { url: '/settings', method: 'GET', json: defaultSettingsPayload },
      {
        url: '/upload-topology-file',
        method: 'POST',
        handler: () => {
          uploadCalled = true
          return { status: 200, json: {} }
        },
      },
    ])
    render(<App />)
    const input = await screen.findByLabelText('Upload a topology file')
    const file = new File(['MZ....'], 'malware.exe', {
      type: 'application/octet-stream',
    })
    // user-event's upload() applies the input's accept attribute and would
    // silently drop this file; fire the change event directly to exercise the
    // app's own extension guard.
    fireEvent.change(input, { target: { files: [file] } })
    expect(
      await screen.findByText(/Unsupported file type/),
    ).toBeInTheDocument()
    // The upload endpoint must never be reached for an unsupported extension.
    await new Promise((resolve) => setTimeout(resolve, 100))
    expect(uploadCalled).toBe(false)
    restore()
  })

  it('surfaces a backend validation failure for a malformed topology file', async () => {
    const user = userEvent.setup()
    const restore = installFetchMock([
      { url: '/settings', method: 'GET', json: defaultSettingsPayload },
      {
        url: '/upload-topology-file',
        method: 'POST',
        status: 400,
        json: { detail: "'cvss_type' must be in [0.0, 10.0], got 42." },
      },
    ])
    render(<App />)
    const input = await screen.findByLabelText('Upload a topology file')
    const file = new File(['{"assets":{"plc":{"cvss_type":42}}}'], 'bad.json', {
      type: 'application/json',
    })
    await user.upload(input, file)
    expect(
      await screen.findByText(/'cvss_type' must be in \[0\.0, 10\.0\]/),
    ).toBeInTheDocument()
    restore()
  })
})

describe('Topology file replacement', () => {
  const topologyB: TopologyPayload = {
    assets: {
      plc_1: { kind: 'device', cvss_type: 5.0, consequence_severity: 5.0 },
      hmi_1: { kind: 'device', cvss_type: 3.0, consequence_severity: 3.0 },
    },
    relationships: [['hmi_1', 'plc_1', 'connects-to', false]],
  }

  // The upload endpoint answers differently depending on the file name, so
  // one mock serves the whole A -> B -> A replacement sequence.
  const replacementRoutes = [
    { url: '/settings', method: 'GET', json: defaultSettingsPayload },
    {
      url: '/upload-topology-file',
      method: 'POST',
      handler: async (init?: RequestInit) => {
        const body = init?.body as FormData | null
        const file = body?.get('file') as File | null
        if (file?.name === 'b.json') {
          return {
            status: 200,
            json: {
              asset_count: 2,
              relationship_count: 1,
              topology: topologyB,
            },
          }
        }
        return {
          status: 200,
          json: {
            asset_count: 1,
            relationship_count: 0,
            topology: smallTopology,
          },
        }
      },
    },
  ]

  it('replaces the selected file without refreshing, then can switch back', async () => {
    const user = userEvent.setup()
    const restore = installFetchMock(replacementRoutes)
    render(<App />)
    const input = await screen.findByLabelText('Upload a topology file')

    const fileA = new File([JSON.stringify(smallTopology)], 'a.json', {
      type: 'application/json',
    })
    const fileB = new File([JSON.stringify(topologyB)], 'b.json', {
      type: 'application/json',
    })

    // Initial selection
    await user.upload(input, fileA)
    await screen.findByText(/Loaded a\.json: 1 assets, 0 relationships/)

    // Evidence marked on A must not survive the replacement.
    await user.click(
      screen.getByRole('button', { name: 'Mark plc_1 as Compromised' }),
    )
    expect(
      screen.getByRole('button', { name: 'Mark plc_1 as Compromised' }),
    ).toHaveAttribute('aria-pressed', 'true')

    // Replace A with B through the in-card action; the same mounted input is
    // reused, so no page refresh is involved.
    await user.click(screen.getByRole('button', { name: 'Replace file' }))
    await user.upload(input, fileB)
    await screen.findByText(/Loaded b\.json: 2 assets, 1 relationships/)
    expect(screen.getAllByText('b.json').length).toBeGreaterThan(0)
    // Assessment state tied to A is gone: evidence is cleared, the review
    // panel now describes B.
    expect(
      screen.getByRole('button', { name: 'Mark plc_1 as Compromised' }),
    ).toHaveAttribute('aria-pressed', 'false')

    // Switch back to A — the input value was reset after each change, so the
    // previously-selected file can be chosen again. The earlier "Loaded
    // a.json" toast may still be visible, so assert on the review panel and
    // status bar (exact filename matches) rather than on toast text.
    await user.click(screen.getByRole('button', { name: 'Replace file' }))
    await user.upload(input, fileA)
    await waitFor(() => {
      expect(screen.queryAllByText('a.json').length).toBeGreaterThan(0)
    })
    restore()
  })

  it('collapses the supported-format disclosure by default and toggles it', async () => {
    const user = userEvent.setup()
    const restore = installFetchMock([
      { url: '/settings', method: 'GET', json: defaultSettingsPayload },
    ])
    render(<App />)
    const summary = screen.getByText('Supported topology representations')
    const details = summary.closest('details')!

    // The preset dataset selector is gone — upload is the only workflow.
    expect(
      screen.queryByLabelText('Select a predefined dataset'),
    ).not.toBeInTheDocument()

    // Collapsed by default. jsdom renders details content regardless of the
    // open attribute (the hiding is a browser UA-stylesheet behavior, covered
    // by the Playwright disclosure check), so assert the state attribute.
    expect(details).not.toHaveAttribute('open')

    // Click opens it.
    await user.click(summary)
    expect(details).toHaveAttribute('open')

    // Click again closes it.
    await user.click(summary)
    expect(details).not.toHaveAttribute('open')
    restore()
  })

  it('removes the loaded topology and returns to the empty state', async () => {
    const user = userEvent.setup()
    const restore = installFetchMock(replacementRoutes)
    render(<App />)
    const input = await screen.findByLabelText('Upload a topology file')
    const fileA = new File([JSON.stringify(smallTopology)], 'a.json', {
      type: 'application/json',
    })
    await user.upload(input, fileA)
    await screen.findByText(/Loaded a\.json: 1 assets, 0 relationships/)

    await user.click(screen.getByRole('button', { name: 'Remove' }))

    await screen.findByText(/No topology loaded yet/)
    expect(screen.getByText(/Drag & drop a topology file/)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Run assessment' }),
    ).toBeDisabled()
    restore()
  })
})
