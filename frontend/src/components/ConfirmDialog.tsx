export default function ConfirmDialog({
  pendingDataset,
  onCancel,
  onConfirm,
}: {
  pendingDataset: string | null
  onCancel: () => void
  onConfirm: () => void
}) {
  if (!pendingDataset) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
        <h3 className="text-lg font-semibold">Discard current evidence?</h3>
        <p className="mt-2 text-sm text-slate-300">
          Switching to the {pendingDataset.replace(/_/g, ' ')} preset will clear
          the evidence you've marked on the current topology.
        </p>
        <div className="mt-5 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="rounded-lg bg-rose-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-rose-400"
          >
            Discard and switch
          </button>
        </div>
      </div>
    </div>
  )
}

