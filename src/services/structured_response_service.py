from __future__ import annotations

import json
import re
from typing import Any


FENCED_JSON_PATTERN = re.compile(
    r"```(?:json)?\s*([\s\S]*?)\s*```",
    flags=re.IGNORECASE,
)


def extract_json_value(response_text: str) -> Any:
    """Extract JSON from a plain response, Markdown fence, or surrounding prose."""
    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("AI response is empty.")

    text = response_text.lstrip("\ufeff").strip()
    candidates = [text]
    candidates.extend(match.group(1).strip() for match in FENCED_JSON_PATTERN.finditer(text))

    last_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as error:
            last_error = error

    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character not in "[{":
            continue
        try:
            value, _end = decoder.raw_decode(text[index:])
            return value
        except json.JSONDecodeError as error:
            last_error = error

    detail = f" {last_error}" if last_error is not None else ""
    raise ValueError(f"Could not find valid JSON in the AI response.{detail}")


def extract_json_object(response_text: str) -> dict[str, Any]:
    value = extract_json_value(response_text)
    if not isinstance(value, dict):
        raise ValueError("AI response JSON must be an object.")
    return value
