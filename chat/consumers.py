"""Lightweight shim module.

This module intentionally keeps the public import path ``chat.consumers``
stable while the full implementations live in ``chat.consumers_impl``.
Only re-export the consumer classes here so other imports in the project
keep working without change.
"""

from .consumers_impl.core import ChatConsumer, PresenceConsumer

__all__ = ["ChatConsumer", "PresenceConsumer"]
