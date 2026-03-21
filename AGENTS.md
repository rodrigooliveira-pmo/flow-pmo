# Codex Operating Rules for This Project

## Workflow Orchestration
1. Plan Node Default
- Enter plan mode for any non-trivial task (3+ steps or architectural decisions).
- If execution derails, stop and re-plan immediately.
- Include verification work in the plan, not only implementation.
- Write detailed specs up front to reduce ambiguity.

2. Subagent Strategy
- Use subagents liberally to keep the main context clean.
- Offload research, exploration, and parallel analysis to subagents.
- For complex work, increase parallel exploration via subagents.
- Keep one tack per subagent for focused execution.

3. Self-Improvement Loop
- After any user correction, append the pattern to `tasks/lessons.md`.
- Add explicit rules that prevent repeating the same mistake.
- Iterate on lessons ruthlessly until repeated errors drop.
- Review relevant lessons at the start of each session.

4. Verification Before Done
- Never mark complete without evidence it works.
- Diff behavior between main and changed code when relevant.
- Check quality against staff-level review expectations.
- Run tests, inspect logs, and demonstrate correctness.

5. Demand Elegance (Balanced)
- For non-trivial changes, ask whether a cleaner design exists.
- If a fix feels hacky, rework to an elegant root-cause solution.
- Skip this step for obvious/simple fixes to avoid over-engineering.
- Challenge your own implementation before presenting.

6. Autonomous Bug Fixing
- On bug reports, diagnose and fix directly without hand-holding.
- Use logs, errors, and failing tests as primary evidence.
- Minimize user context switching.
- Fix failing CI tests proactively.

## Task Management
- Plan first: write a checklist in `tasks/todo.md`.
- Verify plan: check in before starting implementation.
- Track progress: mark checklist items done during execution.
- Explain changes: add concise high-level summaries per step.
- Document results: include a review section in `tasks/todo.md`.
- Capture lessons: update `tasks/lessons.md` after user corrections.
- At the end of each prompt execution, generate a suggested commit message text summarizing the change.

## Authentication

- Login via Google OAuth 2.0 implementado em `auth.py` — não reescrever, apenas estender.
- Controle de acesso atual: allowlist estática via `FLOW_PMO_ALLOWED_EMAILS` (env var).
- Futuro: migrar para checagem dinâmica por grupo Workspace via `FLOW_PMO_ALLOWED_GROUP` + service account.
- Redirect URI de produção: `https://flow-pmo.vercel.app/callback` (registrada no Google Cloud Console, projeto `dashboard-fluxo-produtividade`).
- Workspace tem múltiplos domínios (`w1.com.br`, `w1consultoria.com.br`, `w1technology.com.br`) — não validar por sufixo de e-mail nem por `hd == domínio_primário`. Usar `hd` apenas para bloquear contas Gmail pessoais.
- Para rodar localmente: `python -c "from dotenv import load_dotenv; load_dotenv('.env.local'); from api.index import app; app.run(port=3000, debug=True)"`

## Core Principles
- Simplicity first: solve with minimal complexity and minimal surface area.
- No laziness: find root causes, avoid temporary patches.
- Minimal impact: touch only what is necessary to avoid regressions.
