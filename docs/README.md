# Documentation Index

This repository keeps only public-safe, user-facing documentation.

Sections:

- `architecture/`
  - design and implementation architecture
- `integration/`
  - generic guidance for downstream repositories and wrappers
- `templates/`
  - public-safe examples and starter templates

Key documents:

- `architecture/multi-provider-architecture.md`
  - how `ai-translator` evolved from a Claude-only CLI wrapper into a multi-provider tool
- `integration/cross-repo-integration.md`
  - how downstream repositories should call `ai-translator` without embedding provider details
- `repo-organization.md`
  - documentation policy for this public repo
- `templates/dotfiles/`
  - example wrapper/loader/env templates for local environment integration

Not kept here:

- host-specific operations
- private downstream workflow notes
- secret paths or internal endpoints
- transient implementation plans and rollout journals
