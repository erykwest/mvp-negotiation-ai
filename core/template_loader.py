import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

DEFAULT_TEMPLATE_ID = "recruiting_v1"

_TEMPLATE_FILES = {
    DEFAULT_TEMPLATE_ID: Path(__file__).resolve().parent.parent
    / "product"
    / "templates"
    / "negotiation_template_recruiting.json",
}


@lru_cache(maxsize=None)
def _load_template(template_id: str) -> dict:
    template_path = _TEMPLATE_FILES.get(template_id)
    if template_path is None:
        raise ValueError(f"Unknown negotiation template: {template_id}")

    try:
        with template_path.open("r", encoding="utf-8") as handle:
            template = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Failed to load negotiation template '{template_id}': {exc}") from exc

    if not isinstance(template, dict):
        raise ValueError(f"Negotiation template '{template_id}' must be a JSON object.")

    return template


def load_negotiation_template(template_id: str = DEFAULT_TEMPLATE_ID) -> dict:
    return deepcopy(_load_template(template_id))
