from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from .llm_runtime import actor_answer, evaluator, reflector
from .schemas import AttemptTrace, QAExample, ReflectionEntry, RunRecord


def _infer_failure_mode(traces: list[AttemptTrace]) -> str:
    """Infer failure mode from judge reasons across all failed attempts."""
    if not traces or traces[-1].score == 1:
        return "none"
    # Collect all failure reasons
    reasons = " ".join(t.reason.lower() for t in traces if t.score == 0)
    # Check for looping: multiple attempts with the same wrong answer
    if len(traces) > 2:
        answers = [t.answer.lower().strip() for t in traces]
        if len(set(answers)) == 1:  # All attempts gave same wrong answer
            return "looping"
    # incomplete_multi_hop: stopped at first hop, didn't complete the chain
    if any(kw in reasons for kw in ("first hop", "second hop", "multi-hop", "chain", "intermediate", "stopped at", "partial")):
        return "incomplete_multi_hop"
    # entity_drift: wrong entity substitution in second hop
    if any(kw in reasons for kw in ("entity", "substitut", "drift", "wrong entity", "different entity", "confused", "distractor")):
        return "entity_drift"
    return "wrong_final_answer"

@dataclass
class BaseAgent:
    agent_type: Literal["react", "reflexion"]
    max_attempts: int = 1

    _ATTEMPTS_BY_DIFFICULTY: dict[str, int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self._ATTEMPTS_BY_DIFFICULTY = {"easy": 1, "medium": 3, "hard": 5}

    def _get_max_attempts(self, difficulty: str) -> int:
        """Return adaptive max attempts based on question difficulty."""
        return self._ATTEMPTS_BY_DIFFICULTY.get(difficulty, self.max_attempts)

    def run(self, example: QAExample) -> RunRecord:
        reflection_memory: list[str] = []
        reflections: list[ReflectionEntry] = []
        traces: list[AttemptTrace] = []
        final_answer = ""
        final_score = 0
        effective_max = self._get_max_attempts(example.difficulty) if self.agent_type == "reflexion" else 1
        for attempt_id in range(1, effective_max + 1):
            answer, tokens, latency_ms = actor_answer(example, attempt_id, self.agent_type, reflection_memory)
            judge = evaluator(example, answer)
            token_estimate = tokens
            final_answer = answer
            final_score = judge.score
            reflection: ReflectionEntry | None = None
            if self.agent_type == "reflexion" and judge.score == 0 and attempt_id < effective_max:
                reflection = reflector(example, attempt_id, judge)
                reflections.append(reflection)
                reflection_memory.append(reflection.next_strategy)
            trace = AttemptTrace(attempt_id=attempt_id, answer=answer, score=judge.score, reason=judge.reason, reflection=reflection, token_estimate=token_estimate, latency_ms=latency_ms)
            traces.append(trace)
            if judge.score == 1:
                break
        total_tokens = sum(t.token_estimate for t in traces)
        total_latency = sum(t.latency_ms for t in traces)
        failure_mode = _infer_failure_mode(traces)
        return RunRecord(qid=example.qid, question=example.question, gold_answer=example.gold_answer, agent_type=self.agent_type, predicted_answer=final_answer, is_correct=bool(final_score), attempts=len(traces), token_estimate=total_tokens, latency_ms=total_latency, failure_mode=failure_mode, reflections=reflections, traces=traces)

class ReActAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_type="react", max_attempts=1)

class ReflexionAgent(BaseAgent):
    def __init__(self, max_attempts: int = 3) -> None:
        super().__init__(agent_type="reflexion", max_attempts=max_attempts)
