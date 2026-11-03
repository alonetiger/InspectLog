"""Cleanup manager for temp files and resources."""

import atexit
import os
import shutil

from inspectlog.constants import APP_TEMP_DIR
from inspectlog.infra.logging import get_logger

logger = get_logger("cleanup")


class CleanupManager:
    """Tracks and cleans up temporary files and directories.

    Register files/dirs during tests; they are cleaned up on
    explicit call or at process exit.
    """

    def __init__(self):
        self._files: list[str] = []
        self._dirs: list[str] = []
        atexit.register(self.cleanup_all)

    def register_file(self, path: str) -> str:
        """Register a temp file for cleanup. Returns the path for convenience."""
        self._files.append(path)
        return path

    def register_dir(self, path: str) -> str:
        """Register a temp directory for cleanup. Returns the path."""
        self._dirs.append(path)
        return path

    def get_temp_path(self, filename: str) -> str:
        """Get a path in the app temp dir and register it for cleanup.

        Creates the temp directory if needed.
        """
        os.makedirs(APP_TEMP_DIR, exist_ok=True)
        path = os.path.join(APP_TEMP_DIR, filename)
        self.register_file(path)
        return path

    def cleanup_all(self) -> None:
        """Remove all registered temp files and directories."""
        for f in self._files:
            try:
                if os.path.exists(f):
                    os.remove(f)
                    logger.debug("Cleaned up temp file: %s", f)
            except OSError as e:
                logger.warning("Failed to clean up file %s: %s", f, e)
        self._files.clear()

        for d in self._dirs:
            try:
                if os.path.exists(d):
                    shutil.rmtree(d, ignore_errors=True)
                    logger.debug("Cleaned up temp dir: %s", d)
            except OSError as e:
                logger.warning("Failed to clean up dir %s: %s", d, e)
        self._dirs.clear()

    def cleanup_file(self, path: str) -> None:
        """Clean up a specific file immediately."""
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.debug("Cleaned up file: %s", path)
            if path in self._files:
                self._files.remove(path)
        except OSError as e:
            logger.warning("Failed to clean up file %s: %s", path, e)


# Global singleton
cleanup_manager = CleanupManager()
