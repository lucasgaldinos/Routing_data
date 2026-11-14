---
name: ask-clarification-questions
description: >
  Use when a request has multiple plausible interpretations or is missing key details that a quick
  file read cannot resolve. Triggers on "ask me before doing anything", "clarify first",
  "put me in the loop", "don't proceed without confirming", or when you have serious doubts about
  objective, scope, constraints, environment, or safety that would cause wrong work if guessed.
  Do NOT trigger when the request is unambiguous or a config/file read can resolve the uncertainty.
argument-hint: "[what is unclear] [why you cannot proceed without an answer] [user provided an ambiguous or not clear request] [user said 'ask me first']"
---

# Ask Clarifying Questions Before Proceeding

<context>

This is a **user-in-the-loop** workflow skill. When a request is ambiguous or underspecified,
always ask with `vscode_askQuestions` #tool:vscode/askQuestions (or Antigravity's `ask_question`) before acting — do not guess and proceed. The user prefers to be consulted over
having assumptions made silently.
</context>

## Step 1: Decide what to ask

<instructions>

Invoke this skill whenever any of these are unclear:

- **Objective** — what should change vs. stay the same?
- **Done criteria** — what does success look like (examples, edge cases, acceptance tests)?
- **Scope** — which files, components, or users are in/out?
- **Constraints** — compatibility, performance, style, dependencies, timeline?
- **Environment** — language/runtime versions, OS, build/test runner?
- **Safety** — data migration risk, rollout/rollback, destructive side effects?

If any of the above are unclear, proceed to Step 2. When in doubt, ask.
</instructions>

## Step 2: Formulate must-have questions

<instructions>

Before invoking `vscode_askQuestions`, identify every question that eliminates a whole branch of wrong work. Ask **as many questions as needed** — there is no arbitrary cap. Certainty beats speed: if a decision is required to avoid guessing or assuming, ask it, no matter how many questions that produces. Each question should change the implementation fundamentally — not just style or minor preferences.

**Render full context BEFORE opening the question popup:** In VS Code Copilot, invoking `vscode_askQuestions` pauses UI markdown streaming behind the modal dialog. Always write out the complete explanation, concrete code snippets (*"show the ~30 lines first"*), measured data/benchmark numbers, and honest architectural pros/cons in the chat response **first**, and invoke `vscode_askQuestions` / `ask_question` only as the final action of the turn after all context is written.

For each question:

- Prefer multiple-choice options with many alternatives, or open-ended questions when the space of answers is large or hard to enumerate.
- Ground every option in **real architectural trade-offs** (actor–critic framing: memory, complexity, spec fidelity, coupling, failure modes) — never list trivial/artificial pros or cons such as *"changes fewer lines"*.
- Mark the recommended default clearly so the user can accept it in one word.
- Add a "Not sure — use default" option to minimize friction.
- Always set `allowFreeformInput: true` so the user can type a custom answer.

**Always invoke `vscode_askQuestions`** (or the platform's equivalent structured-question tool) — never ask the user to reply in plain prose. The tool returns each answer mapped back to its question, which is what makes branching on answers reliable.

Invoke `vscode_askQuestions` with the structured questions array — one object per question,
following the schema in the example below.
</instructions>

<example>

```python
# Invoke vscode_askQuestions with this structure:
[
  {
    "header": "scope",
    "question": "What is the scope of the change?",
    "options": [
      {"label": "Minimal — only what was asked", "recommended": True},
      {"label": "Refactor while touching the area"},
      {"label": "Not sure — use minimal (default)"}
    ],
    "allowFreeformInput": True
  },
  {
    "header": "compatibility",
    "question": "Compatibility target?",
    "options": [
      {"label": "Current project defaults", "recommended": True},
      {"label": "Also support older versions (specify below)"},
      {"label": "Not sure — use current defaults"}
    ],
    "allowFreeformInput": True
  }
]
```

</example>

## Step 2b: Branch questions on prior answers

<instructions>

Never ask mutually exclusive questions in the same batch. If a later question only makes sense for some answers to an earlier question, do not include it in the initial batch. Split questions into rounds:

1. Ask the branching question(s) first.
2. Wait for the answer.
3. Ask follow-up questions only for the branch the user actually chose.

<example>

Bad — both in one pass (second question is nonsensical if the user chose bananas):

- "Do you prefer apples or bananas?"
- "Should we focus on green apples or red apples?"

Good — two rounds, keyed on the answer:

- Round 1: "Do you prefer apples or bananas?"
- Round 2 (only if "apples"): "Green apples or red apples?"
- Round 2 (only if "bananas"): "Ripe or unripe bananas?"
</example>

`vscode_askQuestions` returns answers mapped to each question, so inspect that result to decide whether a follow-up round is required before asking more.
</instructions>

## Step 2c: Socratic comprehension check mode (when requested)

<instructions>

When the user asks to verify their understanding of an explanation (e.g., *"use askQuestions to check if I understood"*):

1. Present the first-principles mental model (e.g., Schema vs. Instance `__dict__`, Layer 1 Distance Matrix vs. Layer 2 Move Matrix) and a concrete code trace in chat first.
2. Ask 2–4 diagnostic multiple-choice questions targeting subtle misconceptions.
3. If any answer is wrong, immediately state the exact misconception, show a minimal counter-example proving why that option fails, and re-verify before moving on.
</instructions>

## Step 3: Pause before acting

<instructions>

Until the user answers the questions:

- Do **not** run commands, edit files, or produce a plan that depends on the unknowns — partial plans built on guesses get executed and then need to be undone, which costs more time than the pause itself.
- You **may** perform a clearly labeled, low-risk discovery step that does not commit to a direction (e.g., inspect repo structure, read a config file to find other unknowns).
</instructions>

<checkpoint>

If the user says "proceed with your best guess" before answering:

1. List your assumptions as a short numbered list.
2. State what will go wrong if each assumption is incorrect.
3. Ask the user to confirm or correct before starting.

Only skip the checkpoint if the user explicitly says "just go ahead, I trust you."
</checkpoint>

## Step 4: Confirm interpretation, then proceed

<instructions>

Once answers arrive, restate the requirements in 1–3 sentences that cover:

- What will change and what stays the same.
- Key constraints that bound the implementation.
- What success looks like.

Then start work immediately — do not ask further questions unless a new blocker emerges.
</instructions>

<rules>

**Never do these:**

- Don't ask questions answerable by a quick discovery read — it wastes user attention on things the agent can resolve alone, which trains users to ignore your questions.
- Don't reduce every question to a narrow binary choice when the answer space is large — use many options or an open-ended question instead.
- Don't impose an arbitrary question limit — if a decision is needed to avoid guessing or assuming, ask it. Batch questions into rounds based on dependencies, not cut them off at a count.
- Don't ask mutually exclusive questions in the same batch — split dependent questions into follow-up rounds keyed on the prior answer (see Step 2b).
- Don't ask the user to reply in plain prose — always use `vscode_askQuestions` (or the platform's equivalent) so answers map back to each question.
- Don't proceed without confirmation when the user explicitly asked you to pause first — ignoring
  that request breaks trust more than any wrong implementation would.
- Don't ask for "nice to know" details in the same pass as "must have" questions — ask "must have" questions first, and only ask "nice to know" questions in a later round if they still gate correct work.
- Don't ask low-level static-typing or transaction-isolation questions before the functional pipeline, database schema, and output contracts are defined ("architecture precedes typing").
- When the user says an explanation or question was unclear, clarify and illustrate first before re-asking — never repeat the same opaque question.

</rules>

