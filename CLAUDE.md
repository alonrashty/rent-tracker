# London Flat Hunt

Automated rental listing agent for a September 2026 move to London.
Collects, enriches, deduplicates, and surfaces listings for human review.

## Docs
- Architecture & data flow → `docs/architecture.md`
- Search parameters → `docs/search-spec.md`
- TfL integration → `docs/tfl-integration.md`
- Database schema → `docs/schema.md`
- Build plan & progress → `docs/build-plan.md`

## Config
Personal parameters (API keys, areas, budget, email) → `config.md` (git-ignored)
Template → `config.example.md`

## Commands
- `/collection-cycle` — run a full collect → ingest → enrich → digest cycle

## Immutable Rules
1. NEVER contact landlords or generate outreach messages
2. NEVER modify `config.md` programmatically
3. ALWAYS deduplicate by listing URL before inserting to DB
4. NEVER add listings from SpareRoom (whole flats only)
5. NEVER store short lets (minimum tenancy must be 12+ months)
6. After each completed step: update `docs/build-plan.md` (check done items) and `docs/discoveries.md` (non-obvious findings, decisions). Don't batch.
7. At 10% context: stop. Write `docs/session-handoff.md` (current state, last task, next step, open issues); update build-plan.md and discoveries.md. Don't resume until saved.
