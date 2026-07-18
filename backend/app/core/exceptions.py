"""
Application-specific exceptions.

Keeping these distinct from generic Exceptions lets the FastAPI exception
handlers return precise HTTP status codes and messages instead of leaking
stack traces to the client.
"""


class OpsPilotError(Exception):
    """Base class for all application-raised errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InvalidPDFError(OpsPilotError):
    """Raised when an uploaded file is not a valid/readable PDF."""

    def __init__(self, message: str = "The uploaded file is not a valid PDF."):
        super().__init__(message, status_code=400)


class EmptyDocumentError(OpsPilotError):
    """Raised when a PDF contains no extractable text."""

    def __init__(self, filename: str):
        super().__init__(
            f"'{filename}' contains no extractable text (it may be a scanned "
            "image without OCR, or a corrupted file).",
            status_code=422,
        )


class FileTooLargeError(OpsPilotError):
    def __init__(self, filename: str, max_mb: int):
        super().__init__(
            f"'{filename}' exceeds the {max_mb}MB upload limit.", status_code=413
        )


class MissingAPIKeyError(OpsPilotError):
    def __init__(self):
        super().__init__(
            "GOOGLE_API_KEY is not configured on the server. Set it as an "
            "environment variable and restart the service.",
            status_code=500,
        )


class LLMServiceError(OpsPilotError):
    def __init__(self, message: str = "The language model provider failed to respond."):
        super().__init__(message, status_code=502)


class QuotaExceededError(OpsPilotError):
    def __init__(self):
        super().__init__(
            "The AI service is currently unavailable because the Google API quota for this project has been exhausted. Please check your Google Cloud billing and quota settings and try again.",
            status_code=429,
        )


class DocumentNotFoundError(OpsPilotError):
    def __init__(self, document_id: str):
        super().__init__(f"Document '{document_id}' was not found.", status_code=404)


class NoDocumentsUploadedError(OpsPilotError):
    def __init__(self):
        super().__init__(
            "No documents have been uploaded yet. Upload at least one PDF "
            "before starting a chat.",
            status_code=400,
        )
