"""
Mission 01: Dialogic Engine
===========================

Supports:
    - Socratic dialogue
    - Galilean dialogue with Salviati, Simplicio, and Sagredo
    - Deterministic responses
    - Optional OpenAI, Gemini, and Anthropic providers
    - Retry handling for transient provider errors
    - JSON trace export

Usage:
    python mission-01/solution/04_dialogic_engine.py --mode socratic

    python mission-01/solution/04_dialogic_engine.py --mode galilean

    python mission-01/solution/04_dialogic_engine.py --mode all

    python mission-01/solution/04_dialogic_engine.py \
        --mode galilean --rounds 2

    python mission-01/solution/04_dialogic_engine.py \
        --mode all --provider gemini
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ============================================================
# Configuration
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "outputs"
OUTPUT_FILE = OUTPUT_DIR / "dialogue_trace.json"

DEFAULT_TOPIC = (
    "Can scientific knowledge be considered reliable "
    "if all observations are potentially fallible?"
)

VALID_PROVIDERS = {"openai", "gemini", "anthropic"}

RETRYABLE_STATUS_CODES = {
    408,
    429,
    500,
    502,
    503,
    504,
}

MAX_RETRIES = 3
MAX_HISTORY_TURNS = 8


# ============================================================
# Utility functions
# ============================================================

def utc_now() -> str:
    """Return the current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def export_json(
    data: dict[str, Any],
    output_file: Path = OUTPUT_FILE,
) -> None:
    """
    Write JSON atomically.

    Writing to a temporary file first helps prevent a partially
    written trace if execution is interrupted during export.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    temporary_file = output_file.with_suffix(
        output_file.suffix + ".tmp"
    )

    try:
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False,
            )
            file.write("\n")

        temporary_file.replace(output_file)

    finally:
        if temporary_file.exists():
            try:
                temporary_file.unlink()
            except OSError:
                pass


def create_trace(
    mode: str,
    topic: str,
    provider: str | None,
) -> dict[str, Any]:
    """Create the overall trace structure."""
    return {
        "mission": "Mission 01 - Dialogic Engine",
        "mode": mode,
        "topic": topic,
        "requested_provider": provider or "deterministic",
        "started_at": utc_now(),
        "completed_at": None,
        "status": "running",
        "summary": {
            "total_turns": 0,
            "llm_turns": 0,
            "fallback_turns": 0,
            "failed_turns": 0,
        },
        "sessions": [],
        "errors": [],
    }


def create_session(
    mode: str,
    topic: str,
    provider: str | None,
) -> dict[str, Any]:
    """Create a trace for one dialogue session."""
    return {
        "mode": mode,
        "topic": topic,
        "requested_provider": provider or "deterministic",
        "started_at": utc_now(),
        "completed_at": None,
        "status": "running",
        "turns": [],
        "errors": [],
        "summary": {
            "total_turns": 0,
            "llm_turns": 0,
            "fallback_turns": 0,
            "failed_turns": 0,
        },
    }


def extract_status_code(error: Exception) -> int | None:
    """
    Extract an HTTP status code from common SDK exceptions.

    Structured exception attributes are preferred over parsing
    the exception message.
    """
    for attribute in ("status_code", "status", "code"):
        value = getattr(error, attribute, None)

        if isinstance(value, int):
            return value

    response = getattr(error, "response", None)

    if response is not None:
        value = getattr(response, "status_code", None)

        if isinstance(value, int):
            return value

    message = str(error)

    for code in RETRYABLE_STATUS_CODES:
        if str(code) in message:
            return code

    return None


def is_retryable(error: Exception) -> bool:
    """Determine whether an API error may be transient."""
    status_code = extract_status_code(error)

    if status_code in RETRYABLE_STATUS_CODES:
        return True

    error_name = type(error).__name__.lower()
    message = str(error).lower()

    transient_terms = (
        "timeout",
        "timed out",
        "connection reset",
        "connection error",
        "temporarily unavailable",
        "resource exhausted",
        "service unavailable",
        "rate limit",
        "ratelimit",
    )

    return (
        any(term in error_name for term in transient_terms)
        or any(term in message for term in transient_terms)
    )


def call_with_retries(
    operation,
    provider_name: str,
) -> str:
    """
    Execute a provider operation with bounded retries.

    Only transient errors are retried. Authentication errors,
    invalid requests, and other permanent errors are raised.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            result = operation()

            if not isinstance(result, str) or not result.strip():
                raise RuntimeError(
                    f"{provider_name} returned an empty response."
                )

            return result.strip()

        except Exception as error:
            if (
                attempt >= MAX_RETRIES
                or not is_retryable(error)
            ):
                raise

            delay = min(2 ** attempt, 8)
            delay += random.uniform(0, 0.5)

            print(
                f"[WARN] {provider_name} request failed: "
                f"{error}. Retrying in {delay:.1f}s "
                f"({attempt + 1}/{MAX_RETRIES})...",
                file=sys.stderr,
            )

            time.sleep(delay)

    raise RuntimeError(
        f"{provider_name} failed after all retry attempts."
    )


# ============================================================
# Deterministic fallback
# ============================================================

SOCRATIC_FALLBACKS = {
    "INIT": (
        "Let us begin by clarifying the central claim. "
        "What do you mean by reliable scientific knowledge?"
    ),
    "PROBE": (
        "What evidence supports your position, and what "
        "assumptions are you making about that evidence?"
    ),
    "CONTRADICTION_CHECK": (
        "Could an observation contradict your claim? "
        "If so, how would you distinguish a flawed observation "
        "from a flawed explanation?"
    ),
    "REFINEMENT_LOOP": (
        "Can you refine your position to account for uncertainty "
        "while preserving what remains justified by the evidence?"
    ),
    "TERMINATION": (
        "We can conclude that scientific reliability need not "
        "require absolute certainty. It depends on evidence, "
        "critical examination, and openness to revision."
    ),
}


GALILEAN_FALLBACKS = {
    "Salviati": (
        "We should examine the claim through evidence and "
        "reasoning. What observations could support or challenge it?"
    ),
    "Simplicio": (
        "I remain cautious. Our observations and interpretations "
        "can be mistaken, so why should we trust the conclusion?"
    ),
    "Sagredo": (
        "Perhaps we should compare both positions. What evidence "
        "would help us distinguish a reliable explanation "
        "from an unsupported assumption?"
    ),
}


# ============================================================
# Provider integrations
# ============================================================

def generate_openai(prompt: str) -> str:
    """Generate a response using the OpenAI SDK."""
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set in the environment."
        )

    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def operation() -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are participating in an academic "
                        "dialogue. Respond thoughtfully, clearly, "
                        "and concisely. Address the question "
                        "directly and avoid inventing evidence."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.7,
        )

        content = response.choices[0].message.content

        if not content:
            raise RuntimeError(
                "OpenAI returned no message content."
            )

        return content

    return call_with_retries(operation, "OpenAI")


def generate_gemini(prompt: str) -> str:
    """Generate a response using the Google Gen AI SDK."""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set in the environment."
        )

    from google import genai

    client = genai.Client(api_key=api_key)

    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    def operation() -> str:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )

        content = getattr(response, "text", None)

        if not content:
            raise RuntimeError(
                "Gemini returned no text content."
            )

        return content

    return call_with_retries(operation, "Gemini")


def generate_anthropic(prompt: str) -> str:
    """Generate a response using the Anthropic SDK."""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set in the environment."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    model = os.getenv(
        "ANTHROPIC_MODEL",
        "claude-3-5-haiku-latest",
    )

    def operation() -> str:
        response = client.messages.create(
            model=model,
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        text_parts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]

        content = "\n".join(text_parts).strip()

        if not content:
            raise RuntimeError(
                "Anthropic returned no text content."
            )

        return content

    return call_with_retries(operation, "Anthropic")


def generate_response(
    prompt: str,
    provider: str | None,
) -> tuple[str, str, str | None]:
    """
    Generate a response.

    Returns:
        response text,
        actual provider used,
        error message if fallback was necessary.
    """
    if provider is None:
        return (
            "No external provider was requested. "
            "Use the deterministic response for this turn.",
            "deterministic",
            None,
        )

    generators = {
        "openai": generate_openai,
        "gemini": generate_gemini,
        "anthropic": generate_anthropic,
    }

    if provider not in generators:
        raise ValueError(
            f"Unsupported provider: {provider}"
        )

    try:
        response = generators[provider](prompt)

        return response, provider, None

    except Exception as error:
        error_message = (
            f"{type(error).__name__}: {error}"
        )

        print(
            f"[WARN] {provider} failed; using deterministic "
            f"fallback. Details: {error_message}",
            file=sys.stderr,
        )

        return "", "deterministic", error_message


# ============================================================
# Dialogue history
# ============================================================

def format_history(
    turns: list[dict[str, Any]],
    max_turns: int = MAX_HISTORY_TURNS,
) -> str:
    """Format recent dialogue turns for use as LLM context."""
    if not turns:
        return "No previous dialogue turns."

    recent_turns = turns[-max_turns:]
    formatted = []

    for turn in recent_turns:
        speaker = (
            turn.get("persona")
            or turn.get("speaker")
            or turn.get("state")
            or "Participant"
        )

        response = turn.get("response", "")

        formatted.append(
            f"{speaker}: {response}"
        )

    return "\n".join(formatted)


# ============================================================
# Socratic dialogue engine
# ============================================================

class SocraticEngine:
    """Run a structured Socratic dialogue."""

    STATES = [
        "INIT",
        "PROBE",
        "CONTRADICTION_CHECK",
        "REFINEMENT_LOOP",
        "TERMINATION",
    ]

    def __init__(
        self,
        topic: str,
        provider: str | None,
        trace: dict[str, Any],
    ) -> None:
        self.topic = topic
        self.provider = provider
        self.trace = trace

    def build_prompt(self, state: str) -> str:
        """Construct a context-aware prompt for the current state."""
        history = format_history(self.trace["turns"])

        instructions = {
            "INIT": (
                "Introduce the topic and clarify the central "
                "claim or question."
            ),
            "PROBE": (
                "Ask a probing question about the assumptions, "
                "definitions, or evidence underlying the claim."
            ),
            "CONTRADICTION_CHECK": (
                "Look for a possible contradiction, counterexample, "
                "or limitation in the current reasoning."
            ),
            "REFINEMENT_LOOP": (
                "Help refine the argument in light of the "
                "previous questions and answers."
            ),
            "TERMINATION": (
                "Summarize the strongest conclusions, remaining "
                "uncertainties, and lessons from the dialogue."
            ),
        }

        return f"""
You are an assistant participating in a Socratic dialogue.

Topic:
{self.topic}

Current state:
{state}

Previous dialogue:
{history}

Task:
{instructions[state]}

Requirements:
- Address the topic directly.
- Build on the previous dialogue instead of repeating it.
- Use clear, reasoned language.
- Distinguish evidence from assumptions.
- Do not invent facts, studies, or citations.
- Keep the response concise and suitable for an academic dialogue.
""".strip()

    def fallback_response(self, state: str) -> str:
        """Return the deterministic response for a Socratic state."""
        return SOCRATIC_FALLBACKS[state]

    def run(self) -> dict[str, Any]:
        """Execute the five-state Socratic dialogue."""
        print("\n=== SOCRATIC DIALOGUE ===")
        print(f"Topic: {self.topic}\n")

        try:
            for turn_number, state in enumerate(
                self.STATES,
                start=1,
            ):
                prompt = self.build_prompt(state)

                response, actual_provider, error = (
                    generate_response(
                        prompt,
                        self.provider,
                    )
                )

                if actual_provider == "deterministic":
                    response = self.fallback_response(state)

                turn = {
                    "turn": turn_number,
                    "state": state,
                    "requested_provider": (
                        self.provider or "deterministic"
                    ),
                    "provider": actual_provider,
                    "prompt": prompt,
                    "response": response,
                    "fallback_used": (
                        actual_provider == "deterministic"
                        and self.provider is not None
                    ),
                    "error": error,
                    "timestamp": utc_now(),
                }

                self.trace["turns"].append(turn)

                if error:
                    self.trace["errors"].append({
                        "turn": turn_number,
                        "state": state,
                        "provider": self.provider,
                        "error": error,
                        "timestamp": utc_now(),
                    })

                self.update_summary()

                print(f"[{state}]")
                print(response)
                print()

            self.trace["status"] = self.final_status()

        except KeyboardInterrupt:
            self.trace["status"] = "interrupted"
            raise

        except Exception as error:
            self.trace["status"] = "failed"
            self.trace["errors"].append({
                "error": (
                    f"{type(error).__name__}: {error}"
                ),
                "timestamp": utc_now(),
            })
            raise

        finally:
            self.trace["completed_at"] = utc_now()
            self.update_summary()

        return self.trace

    def update_summary(self) -> None:
        """Update session statistics."""
        turns = self.trace["turns"]

        self.trace["summary"] = {
            "total_turns": len(turns),
            "llm_turns": sum(
                turn["provider"] != "deterministic"
                for turn in turns
            ),
            "fallback_turns": sum(
                turn["fallback_used"]
                for turn in turns
            ),
            "failed_turns": sum(
                turn.get("error") is not None
                for turn in turns
            ),
        }

    def final_status(self) -> str:
        """Return a status that reflects fallback usage."""
        if self.trace["errors"]:
            return "completed_with_fallbacks"

        return "completed"


# ============================================================
# Galilean dialogue engine
# ============================================================

class GalileanEngine:
    """
    Run a debate involving three personas:

    Salviati: analytical and evidence-oriented.
    Simplicio: skeptical and inclined to challenge new claims.
    Sagredo: curious and focused on synthesizing arguments.
    """

    PERSONAS = [
        "Salviati",
        "Simplicio",
        "Sagredo",
    ]

    PERSONA_INSTRUCTIONS = {
        "Salviati": (
            "Reason analytically. Examine evidence, test claims, "
            "and explain why conclusions follow from observations."
        ),
        "Simplicio": (
            "Challenge assumptions and express reasonable "
            "skepticism. Identify limitations or alternative "
            "explanations without relying on caricature."
        ),
        "Sagredo": (
            "Act as a thoughtful mediator. Compare the arguments, "
            "identify useful questions, and seek a balanced "
            "understanding."
        ),
    }

    def __init__(
        self,
        topic: str,
        provider: str | None,
        rounds: int,
        trace: dict[str, Any],
    ) -> None:
        self.topic = topic
        self.provider = provider
        self.rounds = rounds
        self.trace = trace

    def build_prompt(
        self,
        persona: str,
        round_number: int,
    ) -> str:
        """Build a persona-specific prompt with dialogue history."""
        history = format_history(self.trace["turns"])

        return f"""
You are participating in a Galilean-style philosophical debate.

Topic:
{self.topic}

Your persona:
{persona}

Your perspective:
{self.PERSONA_INSTRUCTIONS[persona]}

Round:
{round_number} of {self.rounds}

Previous dialogue:
{history}

Instructions:
- Stay consistent with your assigned perspective.
- Respond to the arguments already made.
- Develop the discussion instead of merely repeating earlier points.
- Be intellectually honest and distinguish evidence from opinion.
- Do not invent studies, facts, or citations.
- Keep the response concise and appropriate for an academic debate.
""".strip()

    def fallback_response(self, persona: str) -> str:
        """Return the deterministic fallback for a persona."""
        return GALILEAN_FALLBACKS[persona]

    def run(self) -> dict[str, Any]:
        """Execute the requested number of debate rounds."""
        print("\n=== GALILEAN DIALOGUE ===")
        print(f"Topic: {self.topic}")
        print(f"Rounds: {self.rounds}\n")

        turn_number = 0

        try:
            for round_number in range(
                1,
                self.rounds + 1,
            ):
                for persona in self.PERSONAS:
                    turn_number += 1

                    prompt = self.build_prompt(
                        persona,
                        round_number,
                    )

                    response, actual_provider, error = (
                        generate_response(
                            prompt,
                            self.provider,
                        )
                    )

                    if actual_provider == "deterministic":
                        response = self.fallback_response(
                            persona
                        )

                    turn = {
                        "turn": turn_number,
                        "round": round_number,
                        "persona": persona,
                        "requested_provider": (
                            self.provider or "deterministic"
                        ),
                        "provider": actual_provider,
                        "prompt": prompt,
                        "response": response,
                        "fallback_used": (
                            actual_provider == "deterministic"
                            and self.provider is not None
                        ),
                        "error": error,
                        "timestamp": utc_now(),
                    }

                    self.trace["turns"].append(turn)

                    if error:
                        self.trace["errors"].append({
                            "turn": turn_number,
                            "round": round_number,
                            "persona": persona,
                            "provider": self.provider,
                            "error": error,
                            "timestamp": utc_now(),
                        })

                    self.update_summary()

                    print(f"[Round {round_number} - {persona}]")
                    print(response)
                    print()

            self.trace["status"] = self.final_status()

        except KeyboardInterrupt:
            self.trace["status"] = "interrupted"
            raise

        except Exception as error:
            self.trace["status"] = "failed"
            self.trace["errors"].append({
                "error": (
                    f"{type(error).__name__}: {error}"
                ),
                "timestamp": utc_now(),
            })
            raise

        finally:
            self.trace["completed_at"] = utc_now()
            self.update_summary()

        return self.trace

    def update_summary(self) -> None:
        """Update session statistics."""
        turns = self.trace["turns"]

        self.trace["summary"] = {
            "total_turns": len(turns),
            "llm_turns": sum(
                turn["provider"] != "deterministic"
                for turn in turns
            ),
            "fallback_turns": sum(
                turn["fallback_used"]
                for turn in turns
            ),
            "failed_turns": sum(
                turn.get("error") is not None
                for turn in turns
            ),
        }

    def final_status(self) -> str:
        """Return a status that reflects fallback usage."""
        if self.trace["errors"]:
            return "completed_with_fallbacks"

        return "completed"


# ============================================================
# Main orchestration
# ============================================================

def update_overall_summary(
    overall_trace: dict[str, Any],
) -> None:
    """Aggregate statistics across all dialogue sessions."""
    sessions = overall_trace["sessions"]

    overall_trace["summary"] = {
        "total_sessions": len(sessions),
        "total_turns": sum(
            session["summary"]["total_turns"]
            for session in sessions
        ),
        "llm_turns": sum(
            session["summary"]["llm_turns"]
            for session in sessions
        ),
        "fallback_turns": sum(
            session["summary"]["fallback_turns"]
            for session in sessions
        ),
        "failed_turns": sum(
            session["summary"]["failed_turns"]
            for session in sessions
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mission 01: Dialogic Engine"
    )

    parser.add_argument(
        "--mode",
        choices=["socratic", "galilean", "all"],
        default="all",
        help="Dialogue mode to execute (default: all).",
    )

    parser.add_argument(
        "--topic",
        type=str,
        default=DEFAULT_TOPIC,
        help="Topic for the dialogue.",
    )

    parser.add_argument(
        "--provider",
        choices=sorted(VALID_PROVIDERS),
        default=None,
        help=(
            "LLM provider. If omitted, deterministic "
            "responses are used."
        ),
    )

    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        help=(
            "Number of Galilean debate rounds "
            "(default: 1)."
        ),
    )

    args = parser.parse_args()

    topic = args.topic.strip()

    if not topic:
        parser.error("--topic must not be empty.")

    if args.rounds < 1:
        parser.error("--rounds must be at least 1.")

    overall_trace = create_trace(
        mode=args.mode,
        topic=topic,
        provider=args.provider,
    )

    # Save an initial trace before running any session.
    export_json(overall_trace)

    print("=" * 60)
    print("MISSION 01: DIALOGIC ENGINE")
    print("=" * 60)
    print(f"Mode: {args.mode}")
    print(f"Provider: {args.provider or 'deterministic'}")
    print(f"Topic: {topic}")
    print()

    engines = []

    if args.mode in ("socratic", "all"):
        engines.append(("socratic", SocraticEngine))

    if args.mode in ("galilean", "all"):
        engines.append(("galilean", GalileanEngine))

    try:
        for mode, engine_class in engines:
            session_trace = create_session(
                mode=mode,
                topic=topic,
                provider=args.provider,
            )

            # Keep the overall trace as the canonical output.
            # Engines modify session_trace only and never write
            # directly to the shared output file.
            if mode == "socratic":
                engine = engine_class(
                    topic=topic,
                    provider=args.provider,
                    trace=session_trace,
                )
                engine.run()

            else:
                engine = engine_class(
                    topic=topic,
                    provider=args.provider,
                    rounds=args.rounds,
                    trace=session_trace,
                )
                engine.run()

            overall_trace["sessions"].append(
                session_trace
            )

            update_overall_summary(overall_trace)

            # Persist progress after every completed session.
            export_json(overall_trace)

        overall_trace["status"] = (
            "completed_with_fallbacks"
            if overall_trace["summary"]["fallback_turns"] > 0
            else "completed"
        )

        return_code = 0

    except KeyboardInterrupt:
        overall_trace["status"] = "interrupted"
        overall_trace["errors"].append({
            "error": "Execution interrupted by user.",
            "timestamp": utc_now(),
        })

        return_code = 130

    except Exception as error:
        overall_trace["status"] = "failed"
        overall_trace["errors"].append({
            "error": f"{type(error).__name__}: {error}",
            "timestamp": utc_now(),
        })

        print(
            f"[ERROR] {type(error).__name__}: {error}",
            file=sys.stderr,
        )

        return_code = 1

    finally:
        overall_trace["completed_at"] = utc_now()
        update_overall_summary(overall_trace)

        try:
            export_json(overall_trace)
        except OSError as error:
            print(
                f"[ERROR] Could not save trace: {error}",
                file=sys.stderr,
            )
            return_code = 1

    print("=" * 60)
    print("EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Status: {overall_trace['status']}")
    print(
        f"Sessions: "
        f"{overall_trace['summary']['total_sessions']}"
    )
    print(
        f"Total turns: "
        f"{overall_trace['summary']['total_turns']}"
    )
    print(
        f"LLM turns: "
        f"{overall_trace['summary']['llm_turns']}"
    )
    print(
        f"Fallback turns: "
        f"{overall_trace['summary']['fallback_turns']}"
    )
    print(
        f"Failed turns: "
        f"{overall_trace['summary']['failed_turns']}"
    )
    print(f"Trace saved to: {OUTPUT_FILE}")

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())