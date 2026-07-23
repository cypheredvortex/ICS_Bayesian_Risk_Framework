import type { ToastItem } from '../types'

export default function Toasts({
  items,
  onDismiss,
}: {
  items: ToastItem[]
  onDismiss: (id: number) => void
}) {
  if (!items.length) return null
  return (
    <div className="fixed right-4 top-4 z-50 flex w-80 flex-col gap-2">
      {items.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={`rounded-lg border px-4 py-3 text-sm shadow-lg backdrop-blur transition ${
            toast.tone === 'error'
              ? 'border-rose-500/40 bg-rose-950/90 text-rose-200'
              : toast.tone === 'success'
                ? 'border-emerald-500/40 bg-emerald-950/90 text-emerald-200'
                : 'border-cyan-500/40 bg-slate-900/95 text-cyan-100'
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <span>{toast.message}</span>
            <button
              onClick={() => onDismiss(toast.id)}
              className="text-slate-400 hover:text-white"
              aria-label="Dismiss notification"
            >
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

