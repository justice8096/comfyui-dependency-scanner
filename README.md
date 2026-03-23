# comfyui-dependency-scanner

Scans ComfyUI workflow JSON files, identifies which custom node packages they require, checks whether those packages are installed, and optionally installs missing ones.

Useful for anyone who shares ComfyUI workflows, sets up new machines, or wants to automate environment setup in CI.

## How It Works

The scanner resolves each `class_type` found in your workflow JSONs through a multi-step process:

1. **UUID proxy nodes** (internal GUI widgets) — skipped automatically
2. **Frontend-only nodes** (e.g. `MarkdownNote`) — skipped, no Python backend
3. **Core ComfyUI nodes** — detected by scanning ComfyUI's own Python files
4. **ComfyUI Manager's extension-node-map.json** — maps class types to GitHub repos
5. **Filesystem scan** of `custom_nodes/*.py` — fallback for nodes not in the registry
6. **Unknown** — flagged for manual review

## Installation

```bash
pip install comfyui-dependency-scanner
```

Or install from source:

```bash
git clone https://github.com/justice8096/comfyui-dependency-scanner.git
cd comfyui-dependency-scanner
pip install -e .
```

## Usage

### Check only (default)

```bash
comfyui-scan ./my-workflows /path/to/ComfyUI
```

### Check and install missing packages

```bash
comfyui-scan ./my-workflows /path/to/ComfyUI --install
```

Installation tries ComfyUI Manager's REST API first, then falls back to `git clone`.

### JSON output (for scripting / CI)

```bash
comfyui-scan ./my-workflows /path/to/ComfyUI --json
```

Returns a JSON object with `installed`, `missing`, and `unknown` arrays. Exit code 1 if anything is missing.

### Custom ComfyUI Manager URL

```bash
comfyui-scan ./my-workflows /path/to/ComfyUI --manager-url http://192.168.1.10:8188
```

## Workflow Formats

The scanner handles both ComfyUI workflow formats:

- **GUI format** — the JSON saved from the ComfyUI web interface (`nodes[]` array with `type` fields)
- **API format** — the JSON used for programmatic submission (`{ "1": { "class_type": "...", "inputs": {...} } }`)

It also handles n8n template expressions (`{{ ... }}`) that may be embedded in API-format JSONs when workflows are called from n8n orchestration.

## Python API

```python
from pathlib import Path
from comfyui_dependency_scanner.scanner import scan

result = scan(
    workflows_dir=Path("./my-workflows"),
    comfyui_dir=Path("/path/to/ComfyUI"),
)

print(f"Custom nodes needed: {result.custom_count}")
print(f"Missing packages: {list(result.missing.keys())}")
print(f"Unknown types: {result.unknown}")
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/ tests/
mypy src/
```

## License

MIT
