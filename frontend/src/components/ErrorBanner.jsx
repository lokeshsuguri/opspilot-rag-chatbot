export default function ErrorBanner({ message, onDismiss }) {
  if (!message) return null;

  return (
    <div className="flex items-start gap-2 border-b border-manifest-red/20 bg-manifest-red/5 px-4 py-2.5 text-sm text-manifest-red">
      <span className="mt-0.5 font-mono text-xs">⚠</span>
      <p className="flex-1">{message}</p>
      <button
        onClick={onDismiss}
        aria-label="Dismiss error"
        className="font-mono text-xs text-manifest-red/70 hover:text-manifest-red"
      >
        ✕
      </button>
    </div>
  );
}
