"""Consumers implementation package.

This package contains the heavy-lifting consumer implementations.
The top-level ``chat.consumers`` module will re-export from here to
keep the public import path stable while allowing the code to be
structured into smaller files.
"""

from .core import ChatConsumer, PresenceConsumer

__all__ = ["ChatConsumer", "PresenceConsumer"]
