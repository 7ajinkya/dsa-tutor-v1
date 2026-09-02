"""AI tutor layer: structured contracts + provider implementations.

Default provider is `builtin` — an offline semantic engine authored by AutoClaw
(rubrics, misconception patterns, hint ladders, generators). The `openai` provider
keeps backward compatibility with any external OpenAI-compatible LLM API. `hybrid`
tries external first and falls back to builtin on any failure.
"""
