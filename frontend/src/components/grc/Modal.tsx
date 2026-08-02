// ═══════════════════════════════════════════════════════════════
// Modal + Form system — the core of full CRUD workflows.
// ═══════════════════════════════════════════════════════════════

import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { Button } from './ui'

// ── Modal ───────────────────────────────────────────────────────

export function Modal({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
  size = 'md',
}: {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children: ReactNode
  footer?: ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
}) {
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', handler)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  const sizes: Record<string, string> = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-3xl',
    xl: 'max-w-5xl',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:p-8">
      <div
        className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      <div
        role="dialog"
        aria-modal="true"
        className={`relative z-10 my-auto w-full ${sizes[size]} rounded-2xl border border-slate-700/60 bg-slate-900 shadow-2xl shadow-slate-950/60`}
      >
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 px-6 py-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
            {subtitle ? <p className="mt-0.5 text-xs text-slate-400">{subtitle}</p> : null}
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200"
            aria-label="Close"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
        {footer ? (
          <div className="flex items-center justify-end gap-3 border-t border-slate-800 px-6 py-4">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  )
}

// ── FormField ───────────────────────────────────────────────────

export function FormField({
  label,
  required,
  error,
  hint,
  children,
}: {
  label: string
  required?: boolean
  error?: string
  hint?: string
  children: ReactNode
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-slate-300">
        {label}
        {required ? <span className="ml-0.5 text-rose-400">*</span> : null}
      </label>
      {children}
      {error ? <p className="mt-1 text-xs text-rose-400">{error}</p> : null}
      {hint && !error ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  )
}

export const inputClass =
  'w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 transition-colors focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500'

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputClass} ${props.className ?? ''}`} />
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={`${inputClass} min-h-[80px] resize-y ${props.className ?? ''}`}
    />
  )
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`${inputClass} appearance-none ${props.className ?? ''}`}
    />
  )
}

export function Checkbox({
  label,
  checked,
  onChange,
  disabled,
}: {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}) {
  return (
    <label
      className={`flex items-center gap-2 text-sm text-slate-300 ${
        disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
      }`}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500 focus:ring-offset-slate-900"
      />
      {label}
    </label>
  )
}

// ── Form actions ────────────────────────────────────────────────

export function FormActions({
  onCancel,
  submitting,
  submitLabel = 'Save',
  cancelLabel = 'Cancel',
}: {
  onCancel: () => void
  submitting?: boolean
  submitLabel?: string
  cancelLabel?: string
}) {
  return (
    <>
      <Button variant="secondary" onClick={onCancel} disabled={submitting}>
        {cancelLabel}
      </Button>
      <Button type="submit" variant="primary" disabled={submitting}>
        {submitting ? 'Saving…' : submitLabel}
      </Button>
    </>
  )
}

