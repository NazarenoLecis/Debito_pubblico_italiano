"""Shared utility namespace for the repository.

The implementation currently lives in io_utils.py to keep backward compatibility
with existing modules. New code should import from scripts/utils.py.
"""

from io_utils import *  # noqa: F401,F403
