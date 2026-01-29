"""
Error types for Biblicus.
"""

from __future__ import annotations


class ExtractionRunFatalError(RuntimeError):
    """
    Fatal extraction run error that should abort the entire run.

    This exception is used for conditions that indicate a configuration or environment problem
    rather than a per-item extraction failure. For example, a selection extractor that depends
    on referenced extraction run manifests treats missing manifests as fatal.
    """
