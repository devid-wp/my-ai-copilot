# Changelog

## 0.1.0 — Unreleased

- Rebuilt Citadex as a CLI-only application.
- Added NVIDIA, Gemini and Ollama provider support.
- Added approval prompts and protected paths.
- Removed shell-based command execution and legacy text actions.
- Added packaging, tests and CI configuration.
- Added interactive `/provider`, `/model`, `/mode`, `/permissions` and `/status` commands.
- Redesigned the terminal UI with rich panels, menus, status badges and command completion.
- Added provider-neutral typed contracts for the tool-calling runtime.
- Added a central tool registry with stable schemas and structured dispatch errors.
- Added secure API-key setup when selecting a cloud provider interactively.
- Fixed password masking remaining enabled after entering a provider API key.
- Migrated built-in tool definitions and runtime dispatch to the central registry.
- Added JSON Schema validation before any tool handler is executed.
- Redesigned tool-call output with compact actions, safe previews and structured results.
- Allowed replacing saved provider keys and rejected invalid NVIDIA key formats.
- Enabled native Ollama tool calls and surfaced local API errors instead of empty replies.
- Fixed streamed Ollama errors and populated the model menu from the local server.
- Centralized tool authorization around risk-aware permission policies.
- Added agent-loop guards for repeated calls, error streaks, pseudo-calls and action summaries.
- Added a cached native-tool compatibility probe before enabling Ollama agent mode.
- Expanded `/status` with provider health, model availability, tools and session diagnostics.
- Added a first-run wizard with one-time API-key setup and remembered defaults.
- Fixed empty cloud chat replies and completed provider switching with model selection.
- Routed conversational prompts safely through chat even while agent mode is enabled.
- Added in-session project switching and actionable handling for paths outside the workspace.
- Added remembered ask/auto permission selection to the agent startup flow.
