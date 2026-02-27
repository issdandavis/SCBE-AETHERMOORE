"""
@file __init__.py
@module browser/extensions
@layer Layer 12, Layer 13
@component Browser Extensions — Document handling, connector dispatch, cloud integration

Headless browser productivity extensions for SCBE AetherBrowse.
"""

from .doc_handler import DocHandler, ExtractedDocument
from .connector_dispatch import ConnectorDispatcher, ConnectorConfig, DispatchResult

__all__ = [
    "DocHandler",
    "ExtractedDocument",
    "ConnectorDispatcher",
    "ConnectorConfig",
    "DispatchResult",
]
