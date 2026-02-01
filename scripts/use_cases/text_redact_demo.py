"""
Use case demo: mark sensitive spans in text using the text redaction utility.

The default behavior is an integration run using a real model and the built-in system prompt.
Use --mock for deterministic local runs that require no external services.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text.models import TextRedactRequest
from biblicus.text.redact import apply_text_redact


def _demo_text() -> str:
    return (
        "Hello Sam,\n\n"
        "Please call me at 555-0100 and email sam@example.com.\n"
        "Thanks,\n"
        "Alex\n"
    )


def _mock_marked_up_text() -> str:
    return (
        "Hello Sam,\n\n"
        "Please call me at <span>555-0100</span> and email <span>sam@example.com</span>.\n"
        "Thanks,\n"
        "Alex\n"
    )


def run_demo(*, mock: bool, model: str) -> Dict[str, object]:
    """
    Run the demo and return a JSON-serializable payload.

    :param mock: If True, use a deterministic mock marked-up string instead of calling a model.
    :type mock: bool
    :param model: Model identifier to use for real runs (ignored when ``mock=True``).
    :type model: str
    :return: JSON-serializable output including markup and extracted spans.
    :rtype: dict[str, object]
    """
    text = _demo_text()
    prompt_template = "Return the phone numbers and email addresses."

    request = TextRedactRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model=model,
            api_key=None,
            response_format="json_object",
            timeout_seconds=300.0,
        ),
        prompt_template=prompt_template,
        max_rounds=10,
        max_edits_per_round=200,
        mock_marked_up_text=_mock_marked_up_text() if mock else None,
    )
    result = apply_text_redact(request)
    return {
        "prompt_template": prompt_template,
        "marked_up_text": result.marked_up_text,
        "spans": [span.model_dump() for span in result.spans],
        "warnings": list(result.warnings),
    }


def build_parser() -> argparse.ArgumentParser:
    """
    Build an argument parser for this demo script.

    :return: Parser for command-line arguments.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Use case demo: mark sensitive spans in text using text redact."
    )
    parser.add_argument("--corpus", required=True, help="Corpus path (accepted for consistency).")
    parser.add_argument("--force", action="store_true", help="Unused; accepted for consistency.")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use a deterministic mock model output instead of calling a real model.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="Model name for real runs (ignored in --mock mode).",
    )
    return parser


def main() -> int:
    """
    Command-line entrypoint.

    :return: Exit code.
    :rtype: int
    """
    args = build_parser().parse_args()
    _ = Path(args.corpus)
    _ = bool(args.force)
    payload = run_demo(mock=bool(args.mock), model=str(args.model))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
