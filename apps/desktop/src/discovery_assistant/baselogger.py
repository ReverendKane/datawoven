# baselogger.py
# coding:utf-8
# #!/usr/bin/python

from discovery_assistant.constants import FRMT_LOG_LONG, TOOL_BASE_PATH
from pathlib import Path
from logging import config
from logging.handlers import RotatingFileHandler
import platform
import sys, io, os, logging

# Remove any pre-existing root handlers to avoid duplicates if this module gets re-imported
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)


class BaseLogger:
    """
    Configure application logging once at startup, then use `logging.getLogger(__name__)`
    anywhere else. Console logs use ColorFormatter; file logs (optional) are plain UTF-8.

    Usage (early in main.py, before creating complex widgets):
        bl = BaseLogger()
        bl.set_logging_configuration(
            log_level=logging.INFO,
            file_config=None,  # or a path string to enable file logging
            file_log_level=logging.ERROR
        )
    """
    def __init__(self):
        # Root logger; handlers will filter actual outputs
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)

        # Paths / defaults from your constants
        self.base_directory = TOOL_BASE_PATH
        # Keep your default file path; only used if file_config is provided or you pass this in
        self.log_file = Path(self.base_directory, '.temp\\logs\\tool.log')

        # Feature flags
        self.color_formatting = True

        # Optional INI-style logging config dir (if you ever call load_configuration_file)
        self.log_configuration_directory = None

        # Handler references
        self.file_handler = None
        self.stream_handler = None

        # Default levels
        self.log_level = logging.INFO
        self.file_log_level = logging.ERROR

    def set_logging_configuration(
        self,
        log_level=logging.INFO,
        file_config=None,              # str | Path | None : path to log file; if None, file logging disabled
        file_log_level=logging.ERROR,
        max_bytes=2_000_000,
        backup_count=3,
    ):
        """Configure console (always) and optional rotating file logging (UTF-8)."""

        self.log_level = log_level
        self.file_log_level = file_log_level

        # --- Build a console stream that won't crash on Windows CP-1252 ---
        stream = self._utf8_console_stream()

        # --- Formatter(s) ---
        # Use your long format string from constants for consistency
        console_formatter = ColorFormatter(FRMT_LOG_LONG) if self.color_formatting else logging.Formatter(FRMT_LOG_LONG)
        file_formatter    = logging.Formatter(FRMT_LOG_LONG)

        # --- Console handler ---
        self.stream_handler = logging.StreamHandler(stream=stream)
        self.stream_handler.setLevel(log_level)
        self.stream_handler.setFormatter(console_formatter)
        # Avoid duplicate console handlers (re-init safe)
        if not any(isinstance(h, logging.StreamHandler) for h in self.logger.handlers):
            self.logger.addHandler(self.stream_handler)

        # --- Optional rotating file handler (UTF-8) ---
        # If caller passed a path (string/Path), use it; otherwise, skip file logging
        if file_config:
            file_path = Path(file_config)
            try:
                os.makedirs(file_path.parent, exist_ok=True)
            except Exception:
                # If parent can't be created, fall back to base .temp\logs
                fallback = Path(self.base_directory, '.temp\\logs\\tool.log')
                os.makedirs(fallback.parent, exist_ok=True)
                file_path = fallback

            self.file_handler = RotatingFileHandler(
                filename=str(file_path),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8"
            )
            self.file_handler.setLevel(file_log_level)
            self.file_handler.setFormatter(file_formatter)

            # Avoid duplicate file handlers (re-init safe, key off filename)
            if not any(isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == str(file_path)
                       for h in self.logger.handlers):
                self.logger.addHandler(self.file_handler)

        # Ensure root level is low enough; handlers still filter
        self.logger.setLevel(logging.DEBUG)

    @staticmethod
    def get_logger(target_module):
        return logging.getLogger(target_module)

    def load_configuration_file(self, config_file='file.conf'):
        """
        Optional: if you keep an INI logging config file, call this to load it.
        It will replace handler config according to that file.
        """
        if not self.log_configuration_directory:
            raise RuntimeError("log_configuration_directory is not set.")
        config.fileConfig(self.log_configuration_directory / config_file, disable_existing_loggers=False)
        _LOGGER = logging.getLogger('Discovery.baselogger')
        _LOGGER.info(f'Logging config file loaded: {config_file}')

    # ----------------- helpers -----------------

    def _utf8_console_stream(self):
        """
        Windows: try to ensure stdout/stderr write UTF-8 (or replace unmappable chars)
        macOS/Linux: terminals are UTF-8 by default; return sys.stdout as-is.
        """
        if platform.system() == "Windows":
            # Reconfigure where possible
            for attr in ("stdout", "stderr"):
                s = getattr(sys, attr, None)
                if s and hasattr(s, "reconfigure"):
                    try:
                        s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
                    except Exception:
                        pass
            base = getattr(sys, "stdout", None)
            if base and hasattr(base, "buffer"):
                try:
                    return io.TextIOWrapper(base.buffer, encoding="utf-8", errors="replace")
                except Exception:
                    pass
            return sys.stdout
        return sys.stdout


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[37m",    # white/gray
        logging.INFO: "\033[36m",     # cyan
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",    # red
        logging.CRITICAL: "\033[41m"  # red background
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"
