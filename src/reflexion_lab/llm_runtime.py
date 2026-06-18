"""LLM runtime using Gemini API — replaces mock_runtime.py for real benchmarking."""
from __future__ import annotations
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM
from .schemas import JudgeResult, QAExample, ReflectionEntry

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.5-flash"

# Disable thinking mode for speed and to avoid UNAVAILABLE errors on short tasks
_THINKING_CONFIG = types.ThinkingConfig(thinking_budget=0)

def _call_with_retry(fn, max_retries: int = 3, base_delay: float = 5.0):
    """Call fn() with exponential backoff on transient errors."""
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            msg = str(e).lower()
            if any(k in msg for k in ("unavailable", "resource_exhausted", "429", "503", "internal")):
                if attempt < max_retries - 1:
                    wait = base_delay * (2 ** attempt)
                    print(f"  [retry {attempt+1}/{max_retries}] {type(e).__name__}: {e!r} — waiting {wait:.0f}s")
                    time.sleep(wait)
                    continue
            raise
    raise RuntimeError(f"All {max_retries} retries failed")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _build_context_text(example: QAExample) -> str:
    return "\n\n".join(
        f"[{chunk.title}]\n{chunk.text}" for chunk in example.context
    )


def _build_actor_user_message(
    example: QAExample,
    reflection_memory: list[str],
) -> str:
    context_text = _build_context_text(example)
    msg = f"## Context\n{context_text}\n\n## Question\n{example.question}"
    if reflection_memory:
        strategies = "\n".join(f"- {s}" for s in reflection_memory)
        msg += f"\n\n## Reflection Memory (apply these strategies!)\n{strategies}"
    return msg


# --------------------------------------------------------------------------- #
# Public API — same signatures as mock_runtime
# --------------------------------------------------------------------------- #

def actor_answer(
    example: QAExample,
    attempt_id: int,
    agent_type: str,
    reflection_memory: list[str],
) -> tuple[str, int, int]:
    """Call the Actor LLM and return (answer, total_tokens, latency_ms)."""
    user_msg = _build_actor_user_message(example, reflection_memory)
    t0 = time.time()
    response = _call_with_retry(lambda: client.models.generate_content(
        model=MODEL,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=ACTOR_SYSTEM,
            thinking_config=_THINKING_CONFIG,
            temperature=1.0,  # required when thinking_budget=0
        ),
    ))
    latency_ms = int((time.time() - t0) * 1000)
    answer = response.text.strip()
    tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0
    return answer, tokens, latency_ms


def evaluator(example: QAExample, answer: str) -> JudgeResult:
    """Call the Evaluator LLM and return a JudgeResult."""
    user_msg = (
        f"Question: {example.question}\n"
        f"Gold answer: {example.gold_answer}\n"
        f"Predicted answer: {answer}"
    )
    response = _call_with_retry(lambda: client.models.generate_content(
        model=MODEL,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=EVALUATOR_SYSTEM,
            thinking_config=_THINKING_CONFIG,
            temperature=1.0,
            response_mime_type="application/json",
            response_schema=JudgeResult,
        ),
    ))
    return response.parsed  # type: ignore[return-value]


def reflector(
    example: QAExample,
    attempt_id: int,
    judge: JudgeResult,
) -> ReflectionEntry:
    """Call the Reflector LLM and return a ReflectionEntry."""
    context_text = _build_context_text(example)
    user_msg = (
        f"Attempt number: {attempt_id}\n"
        f"Question: {example.question}\n"
        f"Wrong answer given: {judge.reason}\n"
        f"Judge feedback: {judge.reason}\n"
        f"Missing evidence: {judge.missing_evidence}\n\n"
        f"Context:\n{context_text}"
    )
    response = _call_with_retry(lambda: client.models.generate_content(
        model=MODEL,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=REFLECTOR_SYSTEM,
            thinking_config=_THINKING_CONFIG,
            temperature=1.0,
            response_mime_type="application/json",
            response_schema=ReflectionEntry,
        ),
    ))
    entry: ReflectionEntry = response.parsed  # type: ignore[assignment]
    # Ensure attempt_id matches the actual attempt (LLM may hallucinate)
    entry.attempt_id = attempt_id
    return entry
