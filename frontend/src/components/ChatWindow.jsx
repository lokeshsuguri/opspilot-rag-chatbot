import { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble.jsx";
import TypingIndicator from "./TypingIndicator.jsx";
import EmptyState from "./EmptyState.jsx";

export default function ChatWindow({ messages, isSending, onSend, hasDocuments, hasIncludedDocuments }) {
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isSending]);

  const canSend = input.trim().length > 0 && !isSending && hasIncludedDocuments;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!canSend) return;
    onSend(input.trim());
    setInput("");
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex h-full flex-col bg-paper">
      <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin px-6 py-6">
        {messages.length === 0 ? (
          <EmptyState hasDocuments={hasDocuments} />
        ) : (
          <div className="mx-auto flex max-w-2xl flex-col gap-4">
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
            {isSending && <TypingIndicator />}
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="border-t border-ink-200 bg-paper px-6 py-4">
        <div className="mx-auto flex max-w-2xl items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder={
              hasIncludedDocuments
                ? "Ask a question about your documents…"
                : "Upload and check at least one document to start chatting"
            }
            disabled={!hasIncludedDocuments}
            className="max-h-32 flex-1 resize-none rounded-xl border border-ink-200 bg-white px-4 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-manifest-amber disabled:cursor-not-allowed disabled:bg-ink-200/30"
          />
          <button
            type="submit"
            disabled={!canSend}
            className="shrink-0 rounded-xl bg-ink-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-ink-800 disabled:cursor-not-allowed disabled:opacity-30"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
