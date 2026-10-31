"""Deterministic tools for the release-notes harness. Standard library only."""


class ToolError(ValueError):
    """Raised for invalid input; the server reports it as isError: true."""
