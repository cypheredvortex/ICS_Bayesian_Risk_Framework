// ═══════════════════════════════════════════════════════════════
// Reusable form builder for GRC entity CRUD
// Provides a structured way to create/edit forms with fields
// ═══════════════════════════════════════════════════════════════

import type { ReactNode } from 'react'
import { FormField, inputClass, Select, TextArea, TextInput, Checkbox } from './Modal'
import { Button } from './ui'

export type FieldType = 'text' | 'textarea' | 'select' | 'number' | 'checkbox' | 'date' | 'hidden'

export interface FormFieldConfig {
  name: string
  label: string
  type: FieldType
  required?: boolean
  placeholder?: string
  options?: Array<{ value: string; label: string }>
  hint?: string
  min?: number
  max?: number
  step?: number
}

export interface FormValues {
  [key: string]: unknown
}

export function GrcForm({
  fields,
  values,
  onChange,
  errors,
}: {
  fields: FormFieldConfig[]
  values: FormValues
  onChange: (name: string, value: unknown) => void
  errors?: Record<string, string>
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {fields.map((field) => {
        const error = errors?.[field.name]
        const value = values[field.name]

        if (field.type === 'hidden') return null

        if (field.type === 'checkbox') {
          return (
            <div key={field.name} className="sm:col-span-2">
              <FormField label={field.label} required={field.required} error={error}>
                <Checkbox
                  label={field.label}
                  checked={Boolean(value)}
                  onChange={(checked) => onChange(field.name, checked)}
                />
              </FormField>
            </div>
          )
        }

        if (field.type === 'textarea') {
          return (
            <div key={field.name} className="sm:col-span-2">
              <FormField label={field.label} required={field.required} error={error} hint={field.hint}>
                <TextArea
                  value={String(value ?? '')}
                  onChange={(e) => onChange(field.name, e.target.value)}
                  placeholder={field.placeholder}
                />
              </FormField>
            </div>
          )
        }

        if (field.type === 'select') {
          return (
            <div key={field.name}>
              <FormField label={field.label} required={field.required} error={error} hint={field.hint}>
                <Select
                  value={String(value ?? '')}
                  onChange={(e) => onChange(field.name, e.target.value)}
                >
                  <option value="">{field.placeholder ?? `Select ${field.label}…`}</option>
                  {field.options?.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </Select>
              </FormField>
            </div>
          )
        }

        if (field.type === 'number') {
          return (
            <div key={field.name}>
              <FormField label={field.label} required={field.required} error={error} hint={field.hint}>
                <TextInput
                  type="number"
                  value={value !== null && value !== undefined ? String(value) : ''}
                  onChange={(e) => {
                    const v = e.target.value
                    onChange(field.name, v === '' ? null : Number(v))
                  }}
                  placeholder={field.placeholder ?? field.label}
                  min={field.min}
                  max={field.max}
                  step={field.step}
                />
              </FormField>
            </div>
          )
        }

        if (field.type === 'date') {
          return (
            <div key={field.name}>
              <FormField label={field.label} required={field.required} error={error} hint={field.hint}>
                <TextInput
                  type="date"
                  value={String(value ?? '')}
                  onChange={(e) => onChange(field.name, e.target.value)}
                />
              </FormField>
            </div>
          )
        }

        // Default: text input
        return (
          <div key={field.name}>
            <FormField label={field.label} required={field.required} error={error} hint={field.hint}>
              <TextInput
                value={String(value ?? '')}
                onChange={(e) => onChange(field.name, e.target.value)}
                placeholder={field.placeholder ?? field.label}
              />
            </FormField>
          </div>
        )
      })}
    </div>
  )
}

export function GrcFormActions({
  onCancel,
  submitting,
  submitLabel = 'Save',
  cancelLabel = 'Cancel',
  onDelete,
  deleteLabel = 'Delete',
}: {
  onCancel: () => void
  submitting?: boolean
  submitLabel?: string
  cancelLabel?: string
  onDelete?: () => void
  deleteLabel?: string
}) {
  return (
    <div className="flex items-center gap-3">
      {onDelete ? (
        <Button variant="danger" onClick={onDelete} disabled={submitting} className="mr-auto">
          {deleteLabel}
        </Button>
      ) : null}
      <Button variant="secondary" onClick={onCancel} disabled={submitting}>
        {cancelLabel}
      </Button>
      <Button type="submit" variant="primary" disabled={submitting}>
        {submitting ? 'Saving…' : submitLabel}
      </Button>
    </div>
  )
}

export function GrcFormSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mb-6">
      <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
        {title}
      </h4>
      {children}
    </div>
  )
}
