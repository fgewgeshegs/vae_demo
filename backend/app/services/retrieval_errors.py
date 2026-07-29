class RetrievalUnavailableError(RuntimeError):
    """Raised when the configured retrieval backend cannot serve a request."""


class RetrievalBusyError(RetrievalUnavailableError):
    """Raised when GPU inference capacity is exhausted."""
