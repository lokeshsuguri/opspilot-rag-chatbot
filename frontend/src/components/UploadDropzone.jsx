import { useCallback, useRef, useState } from "react";

const ACCEPTED_TYPE = "application/pdf";

export default function UploadDropzone({ onUpload, isUploading, uploadProgress }) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef(null);

  const handleFiles = useCallback(
    (fileList) => {
      const files = Array.from(fileList).filter((f) => f.type === ACCEPTED_TYPE);
      const rejected = fileList.length - files.length;
      if (files.length > 0) {
        onUpload(files, rejected);
      } else if (rejected > 0) {
        onUpload([], rejected);
      }
    },
    [onUpload]
  );

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (isUploading) return;
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!isUploading) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => !isUploading && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !isUploading) inputRef.current?.click();
      }}
      aria-label="Upload PDF documents"
      className={`group relative cursor-pointer rounded-lg border border-dashed px-4 py-5 text-center transition-colors
        ${isDragging ? "border-manifest-amber bg-manifest-amber/10" : "border-ink-600 hover:border-ink-400"}
        ${isUploading ? "cursor-not-allowed opacity-70" : ""}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        multiple
        className="hidden"
        disabled={isUploading}
        onChange={(e) => {
          if (e.target.files?.length) handleFiles(e.target.files);
          e.target.value = "";
        }}
      />

      {isUploading ? (
        <div className="space-y-2">
          <div className="mx-auto h-1.5 w-full max-w-[180px] overflow-hidden rounded-full bg-ink-700">
            <div
              className="h-full bg-manifest-amber transition-all duration-200"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <p className="font-mono text-[11px] uppercase tracking-wide text-ink-200">
            Processing manifest… {uploadProgress}%
          </p>
        </div>
      ) : (
        <>
          <p className="font-mono text-[11px] uppercase tracking-wider text-ink-400 group-hover:text-ink-200">
            Drop PDFs here
          </p>
          <p className="mt-1 text-xs text-ink-400">or click to browse — up to 50MB each</p>
        </>
      )}
    </div>
  );
}
