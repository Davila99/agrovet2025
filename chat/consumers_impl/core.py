"""Core module: re-export the split consumer implementations.

This keeps the public import path ``chat.consumers_impl.core`` stable
while the real implementations are in smaller files.
"""

from .chat_consumer import ChatConsumer
from .presence_consumer import PresenceConsumer

__all__ = ["ChatConsumer", "PresenceConsumer"]
