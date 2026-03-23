# Attribution

> Record of human and AI contributions to this project.

## Project

- **Name:** comfyui-dependency-scanner
- **Repository:** https://github.com/justice8096/comfyui-dependency-scanner
- **Started:** 2025 (embedded in TarotCardProject)

---

## Contributors

### Human

| Name | Role | Areas |
|------|------|-------|
| Justice E. Chase | Lead developer | Architecture, design, domain logic, review, integration |

### AI Tools Used

| Tool | Model/Version | Purpose |
|------|---------------|---------|
| Claude | Claude Opus 4.6 | Code generation, documentation, testing, research |
| Claude Code | — | Agentic development, refactoring, extraction |
| ComfyUI | API/Docs | Target platform domain knowledge |

---

## Contribution Log

### Original Source Code
Extracted from TarotCardProject/setup_comfyui_nodes.py. Justice designed the scanning/classification architecture including UUID proxy detection, frontend-only filtering, extension-node-map resolution, and filesystem fallback.

| Date | Tag | Description | AI Tool | Human Review |
|------|-----|-------------|---------|--------------|
| 2025-2026 | `human-only` | Original scanning/classification architecture, UUID proxy detection, filtering logic | — | Justice E. Chase |

### Standalone Extraction

| Date | Tag | Description | AI Tool | Human Review |
|------|-----|-------------|---------|--------------|
| 2026-03-21 | `ai-assisted` | Extracted from TarotCardProject into standalone repo, pyproject.toml, CLI wrapper | Claude Code | Architecture decisions, reviewed all code |
| 2026-03-21 | `ai-generated` | Package config, CI/CD workflows, LICENSE | Claude Code | Reviewed and approved |
| 2026-03-21 | `ai-generated` | README documentation | Claude Code | Reviewed, edited |

### Improvements (2026-03-23)

| Date | Tag | Description | AI Tool | Human Review |
|------|-----|-------------|---------|--------------|
| 2026-03-23 | `ai-generated` | Comprehensive test suite (60+ tests), integration tests | Claude Code | Reviewed and approved |
| 2026-03-23 | `ai-assisted` | Documentation enhancements, usage examples | Claude Code | Reviewed and edited |

---

## Commit Convention

Include `[ai:claude]` tag in commit messages for AI-assisted or AI-generated changes. Example:
```
Extract scanning logic and add tests [ai:claude]
```

---

## Disclosure Summary

| Category | Approximate % |
|----------|---------------|
| Human-only code | 30% |
| AI-assisted code | 25% |
| AI-generated (reviewed) | 45% |
| Documentation | 85% AI-assisted |
| Tests | 95% AI-generated |

---

## Notes

- All AI-generated or AI-assisted code is reviewed by a human contributor before merging.
- AI tools do not have repository access or commit privileges.
- This file is maintained manually and may not capture every interaction.
- Original source code was embedded in TarotCardProject before extraction.

---

## License Considerations

AI-generated content may have different copyright implications depending on jurisdiction. See [LICENSE](./LICENSE) for this project's licensing terms. Contributors are responsible for ensuring AI-assisted work complies with applicable policies.
