---
name: domain-modeling
description: The project's domain language layer. Use to load, sharpen, or extend the domain glossary (CONTEXT.md) and ADRs. Invoked by other skills that need the project's domain vocabulary — don't substitute raw file reads.
---

# Domain Modeling

This is the single source of truth for the project's **domain language**. It owns two artefacts:

- **`CONTEXT.md`** — the live domain glossary: every term that has a precise meaning in this codebase, one definition per term. No synonyms, no overloading.
- **`docs/adr/`** — architectural decision records. Each ADR captures one hard-to-reverse decision with its rationale so future sessions don't re-litigate it.

## Loading domain vocabulary

Before naming things, writing tests, or proposing seams, read `CONTEXT.md` (if it exists) so the vocabulary you use matches the project's language exactly.

## Updating domain vocabulary

When a term is introduced, sharpened, or resolved during a session:

- **New term** → add it to `CONTEXT.md`. Create the file lazily if it doesn't exist.
- **Fuzzy term** → challenge it: does it mean two things? Split it. Does it duplicate another entry? Pick one and redirect.
- **Overloaded term** (one word doing several jobs) → split into distinct terms, update every reference in `CONTEXT.md`.

## Recording architectural decisions (ADRs)

When a decision is hard-to-reverse and load-bearing for future sessions, offer to record it as an ADR:

> "Want me to record this as an ADR so future sessions don't re-suggest it?"

Only offer when the reason would genuinely block a future explorer from re-suggesting the same thing. Skip ephemeral reasons ("not worth it right now") and self-evident ones.

Save to `docs/adr/NNNN-<dash-case-title>.md`, incrementing the number. Minimal format:

```markdown
# ADR-NNNN: <Title>

**Status:** Accepted

## Decision

One paragraph: what was decided and why.

## Consequences

What this rules out, and what it enables.
```
