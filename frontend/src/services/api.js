import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 60000, // generous timeout: PDF ingestion + Gemini calls can be slow on free tiers
});

/**
 * Normalizes any axios error into a plain string message the UI can display,
 * preferring the backend's structured { detail } body when present.
 */
function toErrorMessage(error) {
  if (error.response?.data?.detail) {
    return error.response.data.detail;
  }
  if (error.code === "ECONNABORTED") {
    return "The request timed out. The server may be under load — try again in a moment.";
  }
  if (error.message === "Network Error") {
    return "Could not reach the OpsPilot server. Check your connection or try again shortly.";
  }
  return error.message || "Something went wrong.";
}

export async function uploadDocuments(files, onProgress) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  try {
    const res = await client.post("/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (event) => {
        if (onProgress && event.total) {
          onProgress(Math.round((event.loaded * 100) / event.total));
        }
      },
    });
    return res.data;
  } catch (error) {
    throw new Error(toErrorMessage(error));
  }
}

export async function listDocuments() {
  try {
    const res = await client.get("/documents");
    return res.data;
  } catch (error) {
    throw new Error(toErrorMessage(error));
  }
}

export async function deleteDocument(documentId) {
  try {
    const res = await client.delete(`/documents/${documentId}`);
    return res.data;
  } catch (error) {
    throw new Error(toErrorMessage(error));
  }
}

export async function sendChatMessage(message, sessionId, documentIds) {
  try {
    const res = await client.post("/chat", {
      message,
      session_id: sessionId,
      document_ids: documentIds ?? null,
    });
    return res.data;
  } catch (error) {
    throw new Error(toErrorMessage(error));
  }
}

export async function checkHealth() {
  try {
    const res = await client.get("/health");
    return res.data;
  } catch (error) {
    throw new Error(toErrorMessage(error));
  }
}
