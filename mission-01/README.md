# Mission 01: The Architecture of Argument

**Course:** Conversational AI — Winter Semester 2026/27
**Operational Unit:** USSE Noosphere Bridge Crew

---

## 1. Mission Overview

This mission explores two approaches to structured dialogue and reasoning:

1. **Socratic Discovery** — Examining claims, questioning assumptions, identifying contradictions, evaluating evidence, and refining definitions.
2. **Galilean Debate** — Exploring competing arguments through three personas: Salviati (advocate), Simplicio (skeptic), and Sagredo (mediator).

The objective is to develop a dialogue protocol that prioritises reasoned examination over simple agreement or persuasion.

## 2. Mission Deliverables

| File | Description |
|---|---|
| `ps01_briefing.md` | Official mission specification |
| `01_Alignment_Brief.md` | Discovery versus persuasion and Socratic alignment |
| `02_Socratic_Protocol_Map.md` | Dialogue state machine and refinement protocol |
| `03_Galilean_Sandbox.md` | Three-persona ethical debate and audit |
| `04_dialogic_engine_starter.py` | Original Python starter file |
| `05_Execution_Transcript.md` | Execution report and test record |
| `solution/04_dialogic_engine.py` | Working Python dialogue engine |
| `solution/outputs/dialogue_trace.json` | Saved execution trace |

**Note:** The local starter download does not contain the notebook and Markdown templates mentioned in the original starter README. The completed Markdown deliverables and working Python implementation are maintained separately in this working copy.

## 3. Project Structure

```text
mission-01/
├── ps01_briefing.md
├── 01_Alignment_Brief.md
├── 02_Socratic_Protocol_Map.md
├── 03_Galilean_Sandbox.md
├── 04_dialogic_engine_starter.py
├── 05_Execution_Transcript.md
├── README.md
├── outputs/
│   └── dialogue_trace.json
└── solution/
    ├── 04_dialogic_engine.py
    └── outputs/
        └── dialogue_trace.json
```

## 4. Environment Setup

Run the following commands from the project root.

Activate the existing virtual environment:

```bash
source .venv/bin/activate
```

Check the Python version:

```bash
python --version
```

Check the dialogue engine's available options:

```bash
python mission-01/solution/04_dialogic_engine.py --help
```

## 5. Running the Dialogue Engine

### Run both dialogue modes

```bash
python mission-01/solution/04_dialogic_engine.py --mode all
```

### Run the Socratic dialogue

```bash
python mission-01/solution/04_dialogic_engine.py --mode socratic
```

### Run the Galilean debate

```bash
python mission-01/solution/04_dialogic_engine.py --mode galilean --rounds 2
```

The engine uses deterministic responses by default. Live provider integration requires the appropriate SDK, valid credentials, and configuration. Do not commit API keys or other secrets.

## 6. Verification and Test Results

The following local checks have passed:

- [x] Python syntax compilation.
- [x] Engine help command.
- [x] Deterministic execution of both dialogue modes.
- [x] Completion of two sessions with eight total turns.
- [x] JSON parsing of the saved dialogue trace.
- [x] No failed turns in the recorded deterministic run.
- [x] No fallback turns in the recorded deterministic run.

**Live provider calls have not yet been verified.** Deterministic execution confirms the local dialogue flow, not the quality or availability of external language-model services.

## 7. Interpretation and Limitations

The Socratic protocol is designed to test assumptions, reveal contradictions, and refine definitions rather than simply confirm an initial claim.

The Galilean protocol distributes argumentative roles among an advocate, a skeptic, and a mediator. This structure is intended to expose weaknesses and encourage balanced examination.

Any illustrative dialogue or synthetic debate output should be treated as a demonstration of the protocol, not as empirical evidence that a language model is unbiased or consistently resistant to sycophancy. Such claims require systematic evaluation with recorded prompts, model versions, repeated trials, and explicit scoring criteria.

## 8. Squad Review and Sign-Off

Complete these fields after the relevant officer has reviewed and approved the deliverables.

- [ ] **Historical Archivist** — Name: __________ Date: __________
- [ ] **Protocol Specialist** — Name: __________ Date: __________
- [ ] **Ethical Navigator** — Name: __________ Date: __________
- [ ] **Core Architect** — Name: __________ Date: __________

Do not mark an item as approved until the relevant officer has reviewed it.

## 9. Final Submission Checklist

- [ ] Review all three Markdown deliverables.
- [ ] Inspect the Python implementation.
- [ ] Run the engine in both dialogue modes.
- [ ] Inspect the generated JSON trace.
- [ ] Complete any required live-provider testing.
- [ ] Obtain the required squad sign-offs.
- [ ] Publish the completed project to the agreed public GitHub repository.
- [ ] Confirm that no API keys, credentials, or other secrets are included.
- [ ] Submit the public repository URL through the course portal under:

  **Week 1 → Mission 1 → Problem Set ps01 & Submission**

## 10. Reference

Official course repository:

https://github.com/Unisvet/couse-c-ai
