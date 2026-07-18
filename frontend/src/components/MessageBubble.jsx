function CitationChip({ citation }) {
  return (
    <span
      title={citation.snippet}
      className="inline-flex items-center gap-1 rounded border border-ink-600 bg-ink-800 px-1.5 py-0.5 font-mono text-[10px] text-ink-200 shadow-tag"
    >
      <span className="text-manifest-amber">▸</span>
      {citation.filename} · p.{citation.page_number}
    </span>
  );
}

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-br-sm bg-ink-900 px-4 py-2.5 text-sm text-white">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] space-y-2">
        <div
          className={`rounded-2xl rounded-bl-sm border px-4 py-2.5 text-sm leading-relaxed ${
            message.isError
              ? "border-manifest-red/30 bg-manifest-red/5 text-manifest-red"
              : message.grounded === false
              ? "border-ink-200 bg-white text-ink-600 italic"
              : "border-ink-200 bg-white text-ink-900"
          }`}
        >
          {message.content}
        </div>
        {message.citations?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {message.citations.map((c, i) => (
              <CitationChip key={`${c.document_id}-${c.page_number}-${i}`} citation={c} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
