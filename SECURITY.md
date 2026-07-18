# Security policy

Supported security fixes target the latest release on the `main` branch.

Do not publish vulnerabilities or real API keys in a public issue. Contact the repository owner privately and include reproduction steps, impact and the affected version. Revoke any credential that may have been exposed before sending a report.

Citadex runs model-proposed actions on the user's machine. Confirm prompts are a security boundary: `--yes` deliberately disables that boundary and must only be used in an isolated, trusted workspace.
