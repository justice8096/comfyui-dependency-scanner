# ComfyUI Dependency Scanner

## Purpose
Scans ComfyUI workflow JSON files, identifies required custom node packages, checks installation status, and optionally installs missing ones. Works with both GUI and API format workflows.

## Tools & Stack
- **Python** 3.10+ (no external dependencies)
- **ComfyUI Manager** extension-node-map.json for resolution
- **git** for fallback installation

## Directory Structure
```
src/comfyui_dependency_scanner/
  __init__.py          — Package init, version
  scanner.py           — Core scanning, classification, and installation logic
  cli.py               — CLI entry point (comfyui-scan command)
tests/
  test_scanner.py      — 55 tests covering parsing, classification, installation, and edge cases
```

## Key Commands
```bash
# Check only (default)
comfyui-scan ./workflows /path/to/ComfyUI

# Check and install missing packages
comfyui-scan ./workflows /path/to/ComfyUI --install

# JSON output for CI
comfyui-scan ./workflows /path/to/ComfyUI --json
```

## How Resolution Works (in order)
1. UUID proxy nodes → skip (internal GUI widgets)
2. Frontend-only nodes (MarkdownNote) → skip (no Python backend)
3. Core ComfyUI nodes → skip (scanned from ComfyUI Python files)
4. extension-node-map.json (ComfyUI Manager) → maps type → GitHub URL
5. Filesystem scan of custom_nodes/*.py → fallback match
6. Unknown → flagged for manual check

## Installation Methods
1. ComfyUI Manager REST API (POST /customnode/install) — tried first
2. git clone into custom_nodes/ — fallback

## Technical Notes
- Handles n8n template expressions ({{ }}) embedded in API-format JSONs
- Case-insensitive folder/URL matching for installation detection
- Scans both NODE_CLASS_MAPPINGS (old API) and node_id (new io.ComfyNode API)
- Zero external dependencies — uses only Python stdlib


## LLM Compliance Integration
Scanning ComfyUI workflow dependencies produces evidence useful for AI compliance — documenting which AI models and custom nodes a system relies on.

### Applicable Compliance Areas
- **Supply Chain Risk** (Template 23) — Document third-party AI components and their provenance
- **System Transparency** (Template 01) — The dependency scan output serves as system component documentation
- **Security Assessment** (Template 15) — Identifying all AI components helps with security auditing

### Integration
The scan output (JSON format with `--json` flag) can be fed into the compliance pipeline's config as supply chain evidence.
