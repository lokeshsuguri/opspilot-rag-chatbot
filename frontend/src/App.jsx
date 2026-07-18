import { useEffect, useState, useCallback } from "react";
import Sidebar from "./components/Sidebar.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import ErrorBanner from "./components/ErrorBanner.jsx";
import {
  uploadDocuments,
  listDocuments,
  deleteDocument,
  sendChatMessage,
  checkHealth,
} from "./services/api.js";

function makeSessionId() {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

let messageCounter = 0;
function nextMessageId() {
  messageCounter += 1;
  return `msg-${messageCounter}`;
}

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [includedIds, setIncludedIds] = useState(new Set());
  const [messages, setMessages] = useState([]);
  const [sessionId] = useState(makeSessionId);

  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isSending, setIsSending] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);

  const refreshDocuments = useCallback(async () => {
    try {
      const data = await listDocuments();
      setDocuments(data.documents);
      // Auto-include newly ready documents that haven't been explicitly excluded
      setIncludedIds((prev) => {
        const next = new Set(prev);
        data.documents.forEach((d) => {
          if (d.status === "ready" && !next.has(d.document_id) && !prev.has(`excluded:${d.document_id}`)) {
            next.add(d.document_id);
          }
        });
        return next;
      });
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    (async () => {
      await refreshDocuments();
     try {
  await checkHealth();
  // Backend is healthy. No warning needed.
} catch {
  setError(
    "Could not reach the OpsPilot server. It may still be starting up — try refreshing in a moment."
  );
} finally {
  setIsInitialLoading(false);
}
      
    })();
  }, [refreshDocuments]);

  const handleUpload = async (files, rejectedCount) => {
    if (rejectedCount > 0 && files.length === 0) {
      setError("Only PDF files are supported.");
      return;
    }
    if (rejectedCount > 0) {
      setError(`${rejectedCount} file(s) skipped — only PDF files are supported.`);
    }
    if (files.length === 0) return;

    setIsUploading(true);
    setUploadProgress(0);
    try {
      const result = await uploadDocuments(files, setUploadProgress);
      await refreshDocuments();
      const failed = result.documents.filter((d) => d.status === "failed");
      if (failed.length > 0) {
        setError(
          `${failed.length} document(s) failed to process: ${failed
            .map((d) => `${d.filename} (${d.error_message})`)
            .join("; ")}`
        );
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleToggleIncluded = (documentId) => {
    setIncludedIds((prev) => {
      const next = new Set(prev);
      if (next.has(documentId)) {
        next.delete(documentId);
        next.add(`excluded:${documentId}`);
      } else {
        next.delete(`excluded:${documentId}`);
        next.add(documentId);
      }
      return next;
    });
  };

  const handleDelete = async (documentId) => {
    setDeletingId(documentId);
    try {
      await deleteDocument(documentId);
      setDocuments((prev) => prev.filter((d) => d.document_id !== documentId));
      setIncludedIds((prev) => {
        const next = new Set(prev);
        next.delete(documentId);
        next.delete(`excluded:${documentId}`);
        return next;
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingId(null);
    }
  };

  const handleSend = async (text) => {
    const userMessage = { id: nextMessageId(), role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);
    setError(null);

    const activeDocIds = Array.from(includedIds).filter((id) => !id.startsWith("excluded:"));

    try {
      const response = await sendChatMessage(text, sessionId, activeDocIds);
      setMessages((prev) => [
        ...prev,
        {
          id: nextMessageId(),
          role: "assistant",
          content: response.answer,
          citations: response.citations,
          grounded: response.grounded,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { id: nextMessageId(), role: "assistant", content: err.message, isError: true },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const activeDocCount = Array.from(includedIds).filter((id) => !id.startsWith("excluded:")).length;

  if (isInitialLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-paper">
        <p className="font-mono text-xs uppercase tracking-wider text-ink-400 animate-pulse">
          Connecting to OpsPilot…
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden md:flex-row">
      {/* Mobile top bar */}
      <div className="flex items-center justify-between border-b border-ink-700 bg-ink-900 px-4 py-3 md:hidden">
        <span className="font-mono text-sm font-semibold text-white">OpsPilot</span>
        <button
          onClick={() => setIsSidebarOpen((v) => !v)}
          className="rounded border border-ink-600 px-2.5 py-1 font-mono text-[11px] text-ink-200"
        >
          {isSidebarOpen ? "Close" : `Docs (${documents.length})`}
        </button>
      </div>

      {/* Sidebar: drawer on mobile, static column on desktop */}
      <div
        className={`${
          isSidebarOpen ? "block" : "hidden"
        } absolute inset-0 z-20 md:relative md:block md:w-80 md:shrink-0`}
      >
        <Sidebar
          documents={documents}
          includedIds={includedIds}
          onToggleIncluded={handleToggleIncluded}
          onUpload={handleUpload}
          isUploading={isUploading}
          uploadProgress={uploadProgress}
          onDelete={handleDelete}
          deletingId={deletingId}
        />
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <ErrorBanner message={error} onDismiss={() => setError(null)} />
        <div className="min-h-0 flex-1">
          <ChatWindow
            messages={messages}
            isSending={isSending}
            onSend={handleSend}
            hasDocuments={documents.length > 0}
            hasIncludedDocuments={activeDocCount > 0}
          />
        </div>
      </div>
    </div>
  );
}
