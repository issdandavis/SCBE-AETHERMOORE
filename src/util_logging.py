"""SCBE-AETHERMOORE Utility Logging Module.

Provides structured, Sacred Tongue-aware logging for all SCBE components.
Logs are tagged with tongue affinity, layer origin, and governance context.
"""

import logging
import json
import time
import os
from pathlib import Path

# ── Log directory ──
LOG_DIR = Path(os.environ.get("SCBE_LOG_DIR", Path(__file__).parent.parent / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Tongue colors (for console formatting) ──
TONGUE_ANSI = {
    "KO": "\033[94m",   # blue
    "AV": "\033[33m",   # yellow
    "RU": "\033[91m",   # red
    "CA": "\033[92m",   # green
    "UM": "\033[95m",   # magenta
    "DR": "\033[37m",   # white/silver
}
RESET = "\033[0m"


class SCBEFormatter(logging.Formatter):
    """Custom formatter that includes tongue affinity and layer tags."""

    def format(self, record):
        tongue = getattr(record, "tongue", "")
        layer = getattr(record, "layer", "")
        prefix = ""
        if tongue:
            color = TONGUE_ANSI.get(tongue, "")
            prefix += f"{color}[{tongue}]{RESET} "
        if layer:
            prefix += f"[L{layer}] "
        record.msg = f"{prefix}{record.msg}"
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON-lines formatter for structured log output."""

    def format(self, record):
        entry = {
            "ts": time.time(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "tongue": getattr(record, "tongue", None),
            "layer": getattr(record, "layer", None),
            "agent": getattr(record, "agent", None),
        }
        # Strip None values
        entry = {k: v for k, v in entry.items() if v is not None}
        return json.dumps(entry, ensure_ascii=False)


def get_logger(name, tongue=None, layer=None, level=logging.INFO):
    """Get a configured SCBE logger.

    Args:
        name: Logger name (e.g., 'flock_shepherd', 'polly_pad')
        tongue: Default Sacred Tongue affinity (KO, AV, RU, CA, UM, DR)
        layer: Default SCBE layer number (1-14)
        level: Logging level

    Returns:
        logging.Logger with console + file handlers
    """
    logger = logging.getLogger(f"scbe.{name}")

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    # Console handler with tongue colors
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(SCBEFormatter("%(asctime)s %(levelname)-8s %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(ch)

    # JSON file handler
    log_file = LOG_DIR / f"{name}.jsonl"
    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(JSONFormatter())
    logger.addHandler(fh)

    # Attach defaults via a filter
    class DefaultsFilter(logging.Filter):
        def filter(self, record):
            if not hasattr(record, "tongue"):
                record.tongue = tongue
            if not hasattr(record, "layer"):
                record.layer = layer
            if not hasattr(record, "agent"):
                record.agent = None
            return True

    logger.addFilter(DefaultsFilter())

    return logger


def log_event(logger, msg, tongue=None, layer=None, agent=None, level=logging.INFO):
    """Log an event with optional tongue/layer/agent context.

    Args:
        logger: Logger instance from get_logger()
        msg: Log message
        tongue: Sacred Tongue override (KO, AV, RU, CA, UM, DR)
        layer: SCBE layer override (1-14)
        agent: Agent ID or name
        level: Logging level
    """
    extra = {}
    if tongue:
        extra["tongue"] = tongue
    if layer:
        extra["layer"] = layer
    if agent:
        extra["agent"] = agent
    logger.log(level, msg, extra=extra)
