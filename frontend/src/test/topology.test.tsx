import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import App from '../App'
import { defaultSettingsPayload, installFetchMock, smallTopology } from './helpers'

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
    // both parts since the text is split across nested elements.
    expect(screen.getByText(/Active topology:/)).toBeInTheDocument()
    expect(screen.getByText('my_topology.json')).toBeInTheDocument()
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
