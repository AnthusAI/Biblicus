from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from behave import then, when


def _repo_script_path(context, script_name: str) -> Path:
    script_path = Path("scripts") / "use_cases" / script_name
    return (context.repo_root / script_path).resolve()


def _run_use_case_script(
    context,
    *,
    script_name: str,
    args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if script_name == "sequence_markov_demo.py":
        scenario = getattr(context, "scenario", None)
        if os.environ.get("BIBLICUS_RUN_MARKOV_DEMO") != "1":
            if scenario is not None:
                scenario.skip(
                    "Set BIBLICUS_RUN_MARKOV_DEMO=1 to run the Markov demo integration test."
                )
            return {}
    script_path = _repo_script_path(context, script_name)
    corpus_path = context.workdir / "corpus"

    command: List[str] = [
        sys.executable,
        str(script_path),
        "--corpus",
        str(corpus_path),
        "--force",
    ]
    if args:
        command.extend(args)
    env = {**context.env, **getattr(context, "extra_env", {})}
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("OMP_MAX_ACTIVE_LEVELS", "1")
    env.setdefault("OMP_DYNAMIC", "FALSE")
    env.setdefault("MKL_NUM_THREADS", "1")
    env.setdefault("MKL_THREADING_LAYER", "GNU")
    env.setdefault("OPENBLAS_NUM_THREADS", "1")
    env.setdefault("NUMEXPR_NUM_THREADS", "1")
    env.setdefault("VECLIB_MAXIMUM_THREADS", "1")
    env.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    result = subprocess.run(
        command,
        cwd=context.repo_root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    try:
        payload: Dict[str, Any] = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        if result.returncode != 0:
            raise AssertionError(result.stderr) from exc
        raise AssertionError(f"Expected JSON output, got:\n{result.stdout}") from exc
    context.use_case_output = payload
    return payload


@when('I run the use case demo script "{script_name}"')
def step_run_use_case(context, script_name: str) -> None:
    _run_use_case_script(context, script_name=script_name)


@when('I run the use case demo script "{script_name}" with arguments:')
def step_run_use_case_with_args_table(context, script_name: str) -> None:
    args: List[str] = []
    for row in context.table:
        arg = str(row["arg"]).strip()
        value = str(row["value"]).strip()
        if value.lower() in {"true", "yes"}:
            args.append(arg)
        elif value.lower() in {"false", "no"}:
            continue
        else:
            args.extend([arg, value])
    _run_use_case_script(context, script_name=script_name, args=args)


@then("the demo output includes evidence")
def step_demo_includes_evidence(context) -> None:
    payload = getattr(context, "use_case_output", None)
    assert isinstance(payload, dict)
    evidence = payload.get("evidence", [])
    assert isinstance(evidence, list)
    assert len(evidence) > 0


@then('the demo context pack text contains "{text}"')
def step_demo_context_pack_contains(context, text: str) -> None:
    payload = getattr(context, "use_case_output", None)
    assert isinstance(payload, dict)
    context_pack_text = payload.get("context_pack_text", "")
    assert isinstance(context_pack_text, str)
    assert text.lower() in context_pack_text.lower()


@then('the demo evidence text contains "{text}"')
def step_demo_evidence_text_contains(context, text: str) -> None:
    payload = getattr(context, "use_case_output", None)
    assert isinstance(payload, dict)
    evidence = payload.get("evidence", [])
    assert isinstance(evidence, list)
    evidence_texts = [str(item.get("text", "")) for item in evidence if isinstance(item, dict)]
    joined = "\n".join(evidence_texts)
    assert text in joined


@then('the demo marked up text contains "{text}"')
def step_demo_marked_up_text_contains(context, text: str) -> None:
    payload = getattr(context, "use_case_output", None)
    assert isinstance(payload, dict)
    marked_up_text = payload.get("marked_up_text", "")
    assert isinstance(marked_up_text, str)
    assert text in marked_up_text


@then('the demo transitions dot contains "{text}"')
def step_demo_transitions_dot_contains(context, text: str) -> None:
    payload = getattr(context, "use_case_output", None)
    assert isinstance(payload, dict)
    transitions_dot_path = payload.get("transitions_dot_path", "")
    assert isinstance(transitions_dot_path, str)
    path = Path(transitions_dot_path)
    assert path.is_file(), f"Expected transitions.dot at {path}"
    content = path.read_text(encoding="utf-8")
    assert text in content
