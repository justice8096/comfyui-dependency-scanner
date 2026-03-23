---
name: comfyui-dependency-scan
description: Scan ComfyUI workflows to identify and install missing custom node dependencies
version: 0.1.0
---

# ComfyUI Dependency Scanner Skill

Use this skill when the user wants to check which custom nodes a ComfyUI workflow requires, find missing dependencies, or set up a new ComfyUI environment.

## When to use
- User shares a ComfyUI workflow JSON and asks "what nodes does this need?"
- User wants to verify all dependencies are installed before running a workflow
- User is setting up ComfyUI on a new machine

## How to use

1. Find the workflow JSON file (`.json` extension, contains `nodes` or `extra.workflow` keys)
2. Run the scanner:
   ```bash
   comfyui-scan <workflow.json> --comfyui-dir <path-to-comfyui>
   ```
3. To auto-install missing nodes:
   ```bash
   comfyui-scan <workflow.json> --comfyui-dir <path-to-comfyui> --install
   ```
4. For machine-readable output:
   ```bash
   comfyui-scan <workflow.json> --comfyui-dir <path-to-comfyui> --json
   ```

## Key behaviors
- Handles both GUI-format and API-format workflow JSONs
- Detects UUID proxy nodes and frontend-only nodes gracefully
- Uses ComfyUI Manager's extension-node-map for accurate package resolution
- Falls back to filesystem scanning when the map doesn't cover a node type
- The `--install` flag uses ComfyUI Manager API first, then falls back to git clone
