import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { CoreSettings, ResultPayload, TopologyPayload } from '../types'

export const defaultSettingsPayload: Record<string, unknown> = {
  cvss_mapping: 'logistic',
  cvss_logistic_params: { k: 0.8, x0: 5.0 },
  exposure_weight: 1.0,
  patch_weight: 1.0,
  impact_weight: 1.0,
  propagation_weights: {
    controls: 0.7,
    monitors: 0.2,
    actuates: 0.6,
    'connects-to': 0.5,
    'programs / operates': 0.8,
  },
  firewall_multipliers: { true: 0.3, false: 1.0 },
  risk_thresholds: { critical: 0.75, high: 0.5, moderate: 0.25 },
}

export const smallTopology: TopologyPayload = {
  assets: {
    plc_1: { kind: 'device', cvss_type: 5.0, consequence_severity: 5.0 },
  },
  relationships: [],
}

export const sampleResult: ResultPayload = {
  graph: { nodes: [{ id: 'plc_1', kind: 'device' }], edges: [] },
  posteriors: { plc_1: 0.5 },
  base_probabilities: { plc_1: 0.27 },
  cpts: {
    plc_1: {
      parents: [],
      rows: [{ parent_state: {}, p_compromised: 0.27 }],
    },
  },
  risk_scores: [
    {
      asset: 'plc_1',
      'P(compromised|evidence)': 0.5,
      severity: 5,
      scope_mult: 1,
      impact: 0.5,
      risk: 0.25,
      risk_level: 'Moderate',
    },
  ],
  attack_paths: [],
  summary: {
    topology: 'inline',
    asset_count: 1,
    relationship_count: 0,
    evidence_used: {},
    overall_risk: 0.25,
    risk_level: 'moderate',
    highest_risk_assets: ['plc_1'],
    risk_thresholds: { critical: 0.75, high: 0.5, moderate: 0.25 },
    aggregate_risk: {
      max_risk: 0.25,
      mean_risk: 0.25,
      median_risk: 0.25,
      level_counts: { critical: 0, high: 0, moderate: 1, low: 0 },
      asset_count: 1,
    },
  },
  evidence_used: {},
  timings: { total_time_seconds: 0.12 },
}

export type Route = {
  url: RegExp | string
  method?: string
  status?: number
  json?: unknown
  // When provided, the handler is invoked instead of returning `json`.
  handler?: (
    init?: RequestInit,
  ) => { status: number; json: unknown } | Promise<{ status: number; json: unknown }>
}

// Install a configurable fetch mock; returns a restore function.
export function installFetchMock(routes: Route[]): () => void {
  const original = globalThis.fetch
  globalThis.fetch = (async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> => {
    const url =
      typeof input === 'string'
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url
    const method = (init?.method ?? 'GET').toUpperCase()
    for (const route of routes) {
      const matches =
        typeof route.url === 'string'
          ? url.includes(route.url)
          : route.url.test(url)
      if (!matches) continue
      const routeMethod = (route.method ?? 'GET').toUpperCase()
      if (routeMethod !== method) continue
      if (route.handler) {
        // Handler may be async (e.g. a gated loading-state test): await it so
        // the status/json destructuring sees the resolved value, not a Promise.
        const { status, json } = await route.handler(init)
        return new Response(JSON.stringify(json ?? {}), {
          status,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response(JSON.stringify(route.json ?? {}), {
        status: route.status ?? 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    return new Response(
      JSON.stringify({ detail: `No mock for ${method} ${url}` }),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    )
  }) as typeof fetch
  return () => {
    globalThis.fetch = original
  }
}

export const settingsPayload: CoreSettings = defaultSettingsPayload as CoreSettings

// Common routes for an App test that uploads a topology and runs it.
export function assessmentRoutes(): Route[] {
  return [
    { url: '/settings', method: 'GET', json: defaultSettingsPayload },
    {
      url: '/upload-topology-file',
      method: 'POST',
      json: {
        asset_count: 1,
        relationship_count: 0,
        topology: smallTopology,
      },
    },
    {
      url: '/analyze',
      method: 'POST',
      json: sampleResult,
    },
  ]
}

// Upload a small topology through the file input so the Run assessment
// button becomes enabled.
export async function uploadSmallTopology(user: ReturnType<typeof userEvent.setup>) {
  const input = await screen.findByLabelText('Upload a topology file')
  const file = new File([JSON.stringify(smallTopology)], 'topo.json', {
    type: 'application/json',
  })
  await user.upload(input, file)
  await screen.findByText(/Loaded topo.json: 1 assets, 0 relationships/)
}
