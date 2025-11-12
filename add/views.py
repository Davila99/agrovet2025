"""Compatibility shim: re-export API implementations from the `api` package.

This file keeps older imports working while the real API lives under
`add.api.*` as per project conventions.
"""

from .api.views import *  # noqa: F401,F403
