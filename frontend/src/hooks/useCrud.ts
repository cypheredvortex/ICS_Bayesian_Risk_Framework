// ═══════════════════════════════════════════════════════════════
// Reusable CRUD hook for GRC pages
// Provides create, update, delete state management with modals
// ═══════════════════════════════════════════════════════════════

import { useCallback, useState } from 'react'

export type CrudMode = 'create' | 'edit' | null

export interface CrudState<T> {
  mode: CrudMode
  selected: T | null
  open: boolean
  submitting: boolean
  error: string
}

export function useCrud<T>() {
  const [state, setState] = useState<CrudState<T>>({
    mode: null,
    selected: null,
    open: false,
    submitting: false,
    error: '',
  })

  const openCreate = useCallback(() => {
    setState({ mode: 'create', selected: null, open: true, submitting: false, error: '' })
  }, [])

  const openEdit = useCallback((item: T) => {
    setState({ mode: 'edit', selected: item, open: true, submitting: false, error: '' })
  }, [])

  const close = useCallback(() => {
    setState((prev) => ({ ...prev, open: false, mode: null, selected: null, error: '' }))
  }, [])

  const setSubmitting = useCallback((submitting: boolean) => {
    setState((prev) => ({ ...prev, submitting }))
  }, [])

  const setError = useCallback((error: string) => {
    setState((prev) => ({ ...prev, error }))
  }, [])

  return {
    ...state,
    openCreate,
    openEdit,
    close,
    setSubmitting,
    setError,
  }
}
