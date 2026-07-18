export default function EmptyState({ hasDocuments }) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <div className="mb-3 font-mono text-3xl text-ink-200">▤</div>
      {hasDocuments ? (
        <>
          <p className="text-sm font-medium text-ink-700">Ask about your documents</p>
          <p className="mt-1 max-w-xs text-xs text-ink-400">
            Try: "What is the penalty clause?" or "Summarize the vendor onboarding SOP."
          </p>
        </>
      ) : (
        <>
          <p className="text-sm font-medium text-ink-700">No documents loaded</p>
          <p className="mt-1 max-w-xs text-xs text-ink-400">
            Upload rate cards, SOPs, vendor contracts, or compliance circulars on the left to get
            started.
          </p>
        </>
      )}
    </div>
  );
}
