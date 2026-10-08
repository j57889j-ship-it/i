# V35 Research & Architecture Notes

This package was rebuilt after checking current public documentation and public GitHub examples for the stack used by the project.

## Sources reviewed

- Render Blueprint/Key Value specification: current `type: keyvalue`, internal `ipAllowList: []`, Key Value persistence settings, Web Service health checks.
- Render Web Services/health checks: bind to `0.0.0.0`, health endpoint behavior and service restart model.
- aiogram 3 documentation: Redis FSM storage and webhook model.
- SQLAlchemy async documentation: async engine/session architecture.
- OpenRouter developer documentation: OpenAI-compatible `/chat/completions` API.
- Public GitHub aiogram templates using SQLAlchemy/PostgreSQL/Redis/FastAPI and separated handler/service layers.

## Architecture decisions

1. Keep the existing Telegram UX and admin flows instead of introducing a new framework.
2. Keep PostgreSQL as the source of truth for users, books, questions, attempts and answers.
3. Keep Redis/Valkey for FSM, locks, cooldowns and webhook de-duplication.
4. Keep FastAPI + aiogram webhook for Render.
5. Add only one product feature: AI-generated quiz.
6. Keep AI-generated questions out of the normal question catalog by marking them `source=ai` and `is_active=false`, while still reusing the same attempt/answer scoring pipeline.
7. Validate AI output before touching the database.
8. Prefer soft-deleting books so historical quiz data remains consistent.
9. Make quiz attempt lifecycle idempotent and lock answer/stop paths per attempt.
10. Use `/live` for external uptime monitoring and `/health` for dependency-aware health checks.
