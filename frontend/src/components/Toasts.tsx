import type { ToastItem } from '../types'

const toneClass: Record<ToastItem['tone'], { frame: string; icon: string }> = {
  error: {
    frame: 'border-rose-500/40 bg-rose-950/90 text-rose-200',
    icon: '✕',
  },
  success: {
    frame: 'border-emerald-500/40 bg-emerald-950/90 text-emerald-200',
    icon: '✓',
  },
  info: {
    frame: 'border-cyan-500/40 bg-slate-900/95 text-cyan-100',
    icon: 'ℹ',
  },
}

export default function Toasts({
  items,
  onDismiss,
}: {
  items: ToastItem[]
  onDismiss: (id: number) => void
}) {
  if (!items.length) return null
  return (
    <div
      className="fixed right-4 top-4 z-50 flex w-80 flex-col gap-2"
      aria-live="polite"
    >
      {items.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={`rounded-xl border px-4 py-3 text-sm shadow-card backdrop-blur transition-all duration-200 ${toneClass[toast.tone].frame}`}
        >
          <div className="flex items-start justify-between gap-3">
            <span className="flex items-start gap-2">
              <span className="mt-px text-xs" aria-hidden="true">
                {toneClass[toast.tone].icon}
              </span>
              <span>{toast.message}</span>
            </span>
            <button
              onClick={() => onDismiss(toast.id)}
              className="text-slate-400 transition-colors hover:text-white"
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
