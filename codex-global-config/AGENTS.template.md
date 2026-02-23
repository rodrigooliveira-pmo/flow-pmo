# Global Codex Project Template

Copy this file to the root of a new repository as `AGENTS.md`.

## Workflow Orchestration
1. Plan mode by default for non-trivial work (3+ steps or architecture changes).
2. Stop and re-plan immediately when execution diverges.
3. Put verification in the plan from the start.
4. Write explicit specs before coding.
5. Use focused subagents for research/exploration in parallel.
6. One concern per subagent.

## Execution Quality
1. Never mark done without proof (tests, logs, behavioral diff).
2. For non-trivial changes, challenge for elegance before finalizing.
3. Prefer root-cause fixes over patches/workarounds.
4. Keep changes minimal and scoped.

## Task Management
1. Maintain `tasks/todo.md` with checkable items.
2. Check in against the plan before implementation.
3. Mark progress as work advances.
4. Add review notes with evidence.
5. After any user correction, append a new entry to `tasks/lessons.md`.
6. At the end of each prompt execution, generate a suggested commit message text.

## Self-Improvement Loop
1. Capture correction pattern.
2. Record root cause.
3. Add a concrete prevention rule.
4. Apply the rule in subsequent tasks.

## Suggested Companion Files
- `tasks/todo.md`
- `tasks/lessons.md`
