"""Resolve the application UI scale before importing Qt."""

import json
import logging
import math
import os


MIN_UI_SCALE = 0.5
MAX_UI_SCALE = 3.0
UI_SCALE_ENV = "OPENSHOT_UI_SCALE"


def _validated_scale(value):
    scale = float(value)
    if not math.isfinite(scale):
        raise ValueError("UI scale must be finite")
    return max(MIN_UI_SCALE, min(MAX_UI_SCALE, scale))


def resolve_ui_scale(settings_path, environ=None, logger=None):
    """Return UI scale, preferring an explicit validation/process override."""
    environ = os.environ if environ is None else environ
    logger = logger or logging.getLogger(__name__)

    override = environ.get(UI_SCALE_ENV)
    if override not in (None, ""):
        try:
            return _validated_scale(override)
        except (TypeError, ValueError):
            logger.warning("Ignoring invalid %s value: %r", UI_SCALE_ENV, override)

    scale = 1.0
    try:
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as fh:
                for item in json.load(fh):
                    if item.get("setting") == "ui-scale":
                        scale = _validated_scale(item.get("value", scale))
                        break
    except Exception as exc:
        logger.warning(
            "Failed to read UI scale from %s: %s",
            settings_path,
            exc,
            exc_info=True,
        )
        scale = 1.0

    return scale
