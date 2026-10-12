"""
Mission 01: The Architecture of Argument & Dialogic Protocols
Course: Conversational AI (WS 2026/27)
Starship Unit: USSE Noosphere

Features:
- Socratic Elenchus state machine
- Galilean three-persona ethics debate
- Optional OpenAI, Gemini, and Anthropic integration
- JSON conversation logging and export

Python 3.10+
Deterministic mode requires no API key.
"""

import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional


OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_PROVIDERS = ("openai", "gemini", "anthropic")


# ============================================================
# SOCRATIC ELENCHUS STATE MACHINE
# ============================================================

class SocraticStateEngine:
    VALID_STATES = {
        "INIT",
        "PROBE",
        "CONTRADICTION_CHECK",
        "REFINEMENT_LOOP",
        "TERMINATION",
    }

    def __init__(
        self,
        initial_claim: str,
        max_turns: int = 8,
    ):
        if not initial_claim.strip():
            raise ValueError("The initial claim cannot be empty.")
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1.")

        self.state = "INIT"
        self.claim = initial_claim.strip()
        self.current_claim = self.claim
        self.max_turns = max_turns
        self.history = []
        self.turn_count = 0
        self.outcome: Optional[str] = None
        self.contradiction_detected = False

    def _record(self, message: str) -> str:
        self.turn_count += 1
        self.history.append({
            "turn": self.turn_count,
            "state": self.state,
            "claim": self.current_claim,
            "message": message,
            "outcome": self.outcome,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })
        return message

    def process_step(
        self,
        user_input: str = "",
        refined_claim: Optional[str] = None,
    ) -> str:
        if self.state == "TERMINATION":
            return "[Socratic Engine] Dialogue has already terminated."

        if self.turn_count >= self.max_turns:
            self.state = "TERMINATION"
            self.outcome = "MAX_TURNS"
            return self._record(
                "[Socratic Engine] Maximum turns reached. "
                "Inquiry stopped without claiming that truth "
                "has necessarily been established."
            )

        user_input = user_input.strip()

        if self.state == "INIT":
            self.state = "PROBE"
            message = (
                f"[Socratic Engine] Initial claim: "
                f"'{self.current_claim}'.\n"
                "What assumptions support this claim?"
            )

        elif self.state == "PROBE":
            self.state = "CONTRADICTION_CHECK"
            message = (
                "[Socratic Engine] Examine a counterexample.\n"
                f"Claim: {self.current_claim}\n"
                f"Response: {user_input or '(no response provided)'}\n"
                "Does the counterexample challenge the claim?"
            )

        elif self.state == "CONTRADICTION_CHECK":
            signals = (
                "contradiction",
                "contradict",
                "counterexample",
                "counter-example",
                "inconsistent",
                "conflict",
                "not always",
                "cannot guarantee",
                "does not guarantee",
            )
            self.contradiction_detected = any(
                signal in user_input.lower()
                for signal in signals
            )
            self.state = "REFINEMENT_LOOP"

            if self.contradiction_detected:
                message = (
                    "[Socratic Engine] A possible contradiction "
                    "has been identified.\n"
                    "Please provide a narrower or more precise "
                    "definition of the original claim."
                )
            else:
                message = (
                    "[Socratic Engine] No explicit contradiction "
                    "signal was detected. The claim still needs "
                    "examination. Provide a refined definition "
                    "or a stronger counterexample."
                )

        elif self.state == "REFINEMENT_LOOP":
            if refined_claim and refined_claim.strip():
                self.current_claim = refined_claim.strip()
                self.state = "TERMINATION"
                self.outcome = "REFINED_DEFINITION"
                message = (
                    "[Socratic Engine] A revised definition "
                    "has been recorded.\n"
                    f"Revised claim: {self.current_claim}\n"
                    "Outcome: REFINED_DEFINITION"
                )
            else:
                self.state = "TERMINATION"
                self.outcome = "APORIA"
                message = (
                    "[Socratic Engine] No refined definition "
                    "was supplied.\n"
                    "Outcome: APORIA — unresolved uncertainty."
                )
        else:
            raise RuntimeError(f"Unexpected state: {self.state}")

        return self._record(message)

    def run_demo(self) -> list:
        responses = [
            "",
            "The agent should follow user instructions.",
            (
                "A counterexample exists: obeying an instruction "
                "to harm someone creates a contradiction."
            ),
        ]

        for response in responses:
            if self.state == "TERMINATION":
                break
            print(self.process_step(response))

        if self.state == "REFINEMENT_LOOP":
            print(self.process_step(
                "The definition needs refinement.",
                refined_claim=(
                    "An AI agent should follow legitimate instructions "
                    "while respecting safety, rights, and applicable "
                    "ethical constraints."
                ),
            ))

        return self.history


# ============================================================
# LLM PROVIDER INTERFACE
# ============================================================

def generate_with_llm(provider: str, prompt: str) -> str:
    """Generate text using an external LLM provider."""

    provider = provider.lower().strip()

    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            "Provider must be openai, gemini, or anthropic."
        )

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            raise RuntimeError(
                "Set a valid OPENAI_API_KEY environment variable."
            )

        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            input=prompt,
        )
        result = response.output_text

    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Set the GEMINI_API_KEY environment variable.")

        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
        )
        result = response.text or ""

    else:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Set the ANTHROPIC_API_KEY environment variable."
            )

        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=os.getenv(
                "ANTHROPIC_MODEL",
                "claude-sonnet-4-20250514",
            ),
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        result = "\n".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        )

    if not result or not result.strip():
        raise RuntimeError(f"{provider} returned an empty response.")

    return result.strip()


# ============================================================
# GALILEAN THREE-PERSONA ETHICS DEBATE
# ============================================================

class GalileanEthicsSandbox:
    def __init__(
        self,
        topic: str,
        provider: Optional[str] = None,
    ):
        if not topic.strip():
            raise ValueError("The debate topic cannot be empty.")
        if provider is not None and provider not in SUPPORTED_PROVIDERS:
            raise ValueError("Unsupported LLM provider.")

        self.topic = topic.strip()
        self.provider = provider
        self.history = []

        self.personas = {
            "Salviati": (
                "Advocate: construct the strongest reasonable case "
                "for the proposal. Explain benefits and opportunities."
            ),
            "Simplicio": (
                "Skeptic: challenge assumptions, examine risks, "
                "identify counterexamples, and defend caution."
            ),
            "Sagredo": (
                "Mediator: evaluate both positions and propose "
                "a balanced practical conclusion."
            ),
        }

    def _generate_response(self, speaker: str, context: str) -> str:
        """Generate an LLM response or use a local fallback."""

        if speaker not in self.personas:
            raise ValueError(f"Unknown persona: {speaker}")

        if self.provider:
            prompt = (
                "You are participating in a structured ethics debate.\n\n"
                f"Topic: {self.topic}\n"
                f"Persona: {speaker}\n"
                f"Instructions: {self.personas[speaker]}\n\n"
                "Respond to previous arguments and introduce new reasoning. "
                "Be concise, respectful, and logically consistent. "
                "Do not invent facts or citations.\n\n"
                f"Debate history:\n{context}\n\n"
                f"Write the next contribution from {speaker}."
            )
            return generate_with_llm(self.provider, prompt)

        if speaker == "Salviati":
            return (
                "Open releases can broaden research participation, enable "
                "independent auditing, and encourage innovation. Their "
                "benefits depend on model capabilities and safeguards."
            )

        if speaker == "Simplicio":
            return (
                "Broad access can make harmful uses harder to prevent. "
                "Once model weights are distributed, recalling them is "
                "difficult, and auditing cannot eliminate every risk."
            )

        return (
            "A balanced approach could combine independent evaluation, "
            "transparent documentation, proportionate release controls, "
            "and post-release monitoring."
        )

    def run_debate_turn(
        self,
        speaker: str,
        context: str = "",
        round_number: int = 1,
    ) -> str:
        if speaker not in self.personas:
            raise ValueError(f"Unknown speaker: {speaker}")

        prompt = (
            f"Topic: {self.topic}\n"
            f"Round: {round_number}\n"
            f"Role: {speaker}\n"
            f"Persona instructions: {self.personas[speaker]}\n"
            f"Previous context:\n{context}"
        )

        response = self._generate_response(speaker, context)

        self.history.append({
            "round": round_number,
            "speaker": speaker,
            "topic": self.topic,
            "provider": self.provider or "deterministic",
            "prompt": prompt,
            "response": response,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })

        return f"[{speaker}]: {response}"

    def run_debate(self, rounds: int = 2) -> list:
        if rounds < 1:
            raise ValueError("rounds must be at least 1.")

        context = (
            f"Debate topic: {self.topic}\n"
            "Evaluate the proposal's benefits, risks, and governance."
        )

        for round_number in range(1, rounds + 1):
            print(f"\n--- Debate Round {round_number} ---")

            for speaker in ("Salviati", "Simplicio", "Sagredo"):
                response = self.run_debate_turn(
                    speaker=speaker,
                    context=context,
                    round_number=round_number,
                )
                print(response)
                context += f"\n{response}"

        return self.history


# ============================================================
# JSON EXPORT
# ============================================================

def export_json(filename: str, data: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT_DIR / filename

    with destination.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    return destination


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="USSE Noosphere Dialogic Engine"
    )
    parser.add_argument(
        "--mode",
        choices=("socratic", "galilean", "all"),
        default="all",
    )
    parser.add_argument(
        "--topic",
        default="Open-Sourcing Frontier Foundation Models",
    )
    parser.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        default=None,
        help="Optional external LLM provider.",
    )
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--output", default="dialogue_trace.json")

    args = parser.parse_args()

    if args.rounds < 1:
        parser.error("--rounds must be at least 1.")
    if Path(args.output).name != args.output:
        parser.error("--output must be a filename, not a path.")

    print("=" * 65)
    print("USSE NOOSPHERE — DIALOGIC ENGINE")
    print("Conversational AI | Mission 01")
    print("=" * 65)

    results = {
        "mission": "Mission 01",
        "generated_at": datetime.now().isoformat(),
        "mode": args.mode,
        "topic": args.topic,
        "provider": args.provider or "deterministic",
        "socratic": [],
        "galilean": [],
    }

    if args.mode in ("socratic", "all"):
        print("\n### SOCRATIC ELENCHUS ###")
        engine = SocraticStateEngine(
            "An AI agent is benevolent if it obeys human orders."
        )
        results["socratic"] = engine.run_demo()
        results["socratic_outcome"] = engine.outcome

    if args.mode in ("galilean", "all"):
        print("\n### GALILEAN ETHICS SANDBOX ###")
        sandbox = GalileanEthicsSandbox(
            topic=args.topic,
            provider=args.provider,
        )
        results["galilean"] = sandbox.run_debate(args.rounds)

    json_path = export_json(args.output, results)

    print("\n### EXECUTION COMPLETE ###")
    print(f"Provider: {args.provider or 'deterministic'}")
    print(f"JSON trace saved to: {json_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.")
    except Exception as exc:
        raise SystemExit(f"\nERROR: {exc}") from exc