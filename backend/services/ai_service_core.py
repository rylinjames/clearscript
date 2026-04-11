"""
Core OpenAI client + generation plumbing for ClearScript.

Thin layer responsible for: loading the API key, holding a lazy
singleton client, running generations in a worker thread with an
async timeout + usage logging, and parsing the first JSON object
out of a model response.

Higher-level contract / disclosure / audit prompts live in
ai_service.py. Analysis post-processing lives in contract_enrichment.py.
"""

import os
import json
import asyncio
import logging
import threading
import time
import inspect
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from services.usage_service import log_ai_call

logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

_client = None
_client_lock = threading.Lock()
MODEL = "gpt-5.4-mini"


def _get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    logger.error("OPENAI_API_KEY not set — AI features will fail")
                    raise ValueError("OPENAI_API_KEY not set")
                _client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized")
    return _client


def _extract_first_json_object(text: str) -> str:
    """
    Pull the first complete JSON object out of a model response and return
    it as a clean string ready for json.loads(). Robust to leading
    whitespace, leading preamble, trailing content, and markdown fences.

    Raises ValueError if no JSON object is present at all — the caller
    surfaces that as a 503 with a clear message.
    """
    text = text.strip()
    if not text:
        raise ValueError("Empty response — nothing to parse as JSON")

    if text.startswith("```"):
        text = text[3:]
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.lstrip("\n").rstrip()
        if text.endswith("```"):
            text = text[:-3].rstrip()

    first_brace = text.find("{")
    if first_brace == -1:
        raise ValueError(
            f"No JSON object found in response (got {len(text)} chars, starts with {text[:60]!r})"
        )

    decoder = json.JSONDecoder()
    try:
        obj, _end = decoder.raw_decode(text[first_brace:])
    except json.JSONDecodeError as e:
        snippet = text[first_brace : first_brace + 200]
        raise ValueError(
            f"Could not parse JSON object from model response: {e}. "
            f"First 200 chars after the opening brace: {snippet!r}"
        ) from e

    return json.dumps(obj)


def _infer_operation_name() -> str:
    """
    Walk the call stack to find the public function that triggered this
    AI call (e.g. analyze_contract, generate_audit_letter, parse_spc).
    Used to label the row in ai_calls so usage queries can be split by
    feature without manual tagging at every call site.
    """
    try:
        for frame_info in inspect.stack()[1:8]:
            name = frame_info.function
            if name.startswith("_") or name in ("_generate", "_call", "wrapper"):
                continue
            if name in (
                "analyze_contract",
                "analyze_disclosure",
                "generate_audit_letter",
                "analyze_report",
                "parse_spc",
                "compare_spcs",
                "cross_reference_contract_and_plan",
            ):
                return name
        return "ai_generate"
    except Exception:
        return "ai_generate"


async def _generate(system_prompt: str, user_prompt: str, max_tokens: int = 16000) -> str:
    """
    Run OpenAI generation in a thread to keep it async-compatible.

    Every call is logged to the ai_calls table via usage_service. The
    argument name stays `max_tokens` so existing callers don't change,
    but under the hood we pass `max_completion_tokens` (required by the
    gpt-5 family). 16k default keeps reasoning + structured JSON output
    comfortably within budget.
    """
    client = _get_client()
    operation = _infer_operation_name()
    started = time.perf_counter()
    response_text: str | None = None
    prompt_tokens = 0
    completion_tokens = 0
    error_str: str | None = None
    request_id: str | None = None

    def _call():
        nonlocal prompt_tokens, completion_tokens, request_id
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=max_tokens,
        )
        try:
            usage = response.usage
            if usage is not None:
                prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
                completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        except Exception:
            pass
        try:
            request_id = getattr(response, "id", None)
        except Exception:
            request_id = None

        text = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason
        if not text:
            raise RuntimeError(
                f"OpenAI returned empty content (finish_reason={finish_reason}). "
                f"This usually means max_completion_tokens={max_tokens} was "
                f"consumed entirely by reasoning. Increase the budget."
            )
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3].strip()
        return _extract_first_json_object(text)

    try:
        response_text = await asyncio.wait_for(asyncio.to_thread(_call), timeout=120.0)
        return response_text
    except asyncio.TimeoutError as e:
        error_str = "timeout after 120 seconds"
        raise TimeoutError("OpenAI API call timed out after 120 seconds") from e
    except Exception as e:
        error_str = f"{type(e).__name__}: {e}"
        raise
    finally:
        latency_ms = int((time.perf_counter() - started) * 1000)
        try:
            log_ai_call(
                operation=operation,
                model=MODEL,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_text=response_text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                error=error_str,
                request_id=request_id,
            )
        except Exception as log_err:
            logger.debug(f"AI call logging failed: {log_err}")
