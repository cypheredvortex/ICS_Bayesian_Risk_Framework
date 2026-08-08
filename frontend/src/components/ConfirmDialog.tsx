import { useEffect, useRef } from 'react'

export default function ConfirmDialog({
  pendingDataset,
  onCancel,
  onConfirm,
}: {
  pendingDataset: string | null
  onCancel: () => void
  onConfirm: () => void
}) {
  const cancelRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (pendingDataset) cancelRef.current?.focus()
  }, [pendingDataset])

  if (!pendingDataset) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
    >
      <div className="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-card">
        <h3
          id="confirm-dialog-title"
          className="text-lg font-semibold tracking-tight text-slate-100"
        >
          Discard current evidence?
        </h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-300">
          Switching to the {pendingDataset.replace(/_/g, ' ')} preset will clear
          the evidence you've marked on the current topology.
        </p>
        <div className="mt-5 flex justify-end gap-3">
          <button
            ref={cancelRef}
            onClick={onCancel}
            className="btn btn-secondary"
          >
            Cancel
          </button>
          <button onClick={onConfirm} className="btn btn-danger">
            Discard and switch
          </button>
        </div>
      </div>
    </div>
  )
}
