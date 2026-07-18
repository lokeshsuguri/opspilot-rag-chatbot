import UploadDropzone from "./UploadDropzone.jsx";

const STATUS_STYLES = {
  ready: { dot: "bg-manifest-green", label: "ready" },
  processing: { dot: "bg-manifest-amber animate-pulse", label: "processing" },
  failed: { dot: "bg-manifest-red", label: "failed" },
};

function DocumentRow({ doc, isIncluded, onToggle, onDelete, deletingId }) {
  const status = STATUS_STYLES[doc.status] ?? STATUS_STYLES.processing;
  const isDeleting = deletingId === doc.document_id;

  return (
    <li className="group rounded-md border border-ink-700 bg-ink-800/60 px-3 py-2.5">
      <div className="flex items-start justify-between gap-2">
        <label className="flex min-w-0 flex-1 items-start gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={isIncluded}
            disabled={doc.status !== "ready"}
            onChange={() => onToggle(doc.document_id)}
            className="mt-1 h-3.5 w-3.5 accent-manifest-amber disabled:opacity-30"
            aria-label={`Include ${doc.filename} in chat`}
          />
          <div className="min-w-0">
            <p className="truncate text-sm text-ink-200" title={doc.filename}>
              {doc.filename}
            </p>
            <div className="mt-1 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wide text-ink-400">
              <span className={`h-1.5 w-1.5 rounded-full ${status.dot}`} />
              <span>{status.label}</span>
              {doc.status === "ready" && (
                <span className="text-ink-600">
                  · {doc.page_count}p · {doc.chunk_count} chunks
                </span>
              )}
            </div>
            {doc.status === "failed" && doc.error_message && (
              <p className="mt-1 text-[11px] leading-snug text-manifest-red/90">
                {doc.error_message}
              </p>
            )}
          </div>
        </label>
        <button
          onClick={() => onDelete(doc.document_id)}
          disabled={isDeleting}
          aria-label={`Delete ${doc.filename}`}
          className="shrink-0 rounded px-1.5 py-0.5 font-mono text-[10px] text-ink-400 opacity-0 transition-opacity hover:bg-ink-700 hover:text-manifest-red group-hover:opacity-100 disabled:opacity-50"
        >
          {isDeleting ? "…" : "✕"}
        </button>
      </div>
    </li>
  );
}

export default function Sidebar({
  documents,
  includedIds,
  onToggleIncluded,
  onUpload,
  isUploading,
  uploadProgress,
  onDelete,
  deletingId,
}) {
  return (
    <aside className="flex h-full w-full flex-col bg-ink-900 text-ink-200">
      <div className="border-b border-ink-700 px-4 py-4">
        <h1 className="font-mono text-sm font-semibold tracking-tight text-white">
          OpsPilot
        </h1>
        <p className="mt-0.5 text-[11px] text-ink-400">Document intelligence, grounded.</p>
      </div>

      <div className="px-4 pt-4">
        <UploadDropzone onUpload={onUpload} isUploading={isUploading} uploadProgress={uploadProgress} />
      </div>

      <div className="mt-4 flex-1 overflow-y-auto scrollbar-thin px-4 pb-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-mono text-[11px] uppercase tracking-wider text-ink-400">
            Manifest ({documents.length})
          </h2>
        </div>

        {documents.length === 0 ? (
          <p className="mt-6 text-center text-xs leading-relaxed text-ink-600">
            No documents yet.
            <br />
            Upload PDFs to start building the knowledge base.
          </p>
        ) : (
          <ul className="space-y-2">
            {documents.map((doc) => (
              <DocumentRow
                key={doc.document_id}
                doc={doc}
                isIncluded={includedIds.has(doc.document_id)}
                onToggle={onToggleIncluded}
                onDelete={onDelete}
                deletingId={deletingId}
              />
            ))}
          </ul>
        )}
      </div>

      <div className="border-t border-ink-700 px-4 py-3">
        <p className="font-mono text-[10px] leading-relaxed text-ink-600">
          Answers are grounded strictly in checked documents. Uncheck a document to exclude it from retrieval.
        </p>
      </div>
    </aside>
  );
}
