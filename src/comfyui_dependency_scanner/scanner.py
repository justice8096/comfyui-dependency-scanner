"""
Core scanning and resolution logic for ComfyUI workflow dependencies.

Provides functions to:
  - Parse ComfyUI workflow JSONs (both GUI and API formats)
  - Classify node types (core, custom, UUID proxy, frontend-only)
  - Resolve custom nodes to GitHub repos via ComfyUI Manager's extension-node-map
  - Check installation status via filesystem and git remote matching
  - Install missing packages via ComfyUI Manager API or git clone
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────────

# UUID proxy nodes — internal ComfyUI GUI widgets, not real class_types
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Pure-frontend nodes — rendered by the browser, no Python backend
FRONTEND_ONLY_NODES: set[str] = {
    "MarkdownNote",
}


# ── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class ScanResult:
    """Result of scanning workflows and checking node installation status."""

    # Counts
    total_workflows: int = 0
    total_class_types: int = 0
    core_count: int = 0
    uuid_count: int = 0
    frontend_count: int = 0
    custom_count: int = 0

    # Detailed results
    type_to_files: dict[str, list[str]] = field(default_factory=dict)
    core_types: set[str] = field(default_factory=set)
    uuid_types: set[str] = field(default_factory=set)
    frontend_types: set[str] = field(default_factory=set)
    custom_types: set[str] = field(default_factory=set)

    # Installation status
    installed: list[str] = field(default_factory=list)
    missing: dict[str, str] = field(default_factory=dict)  # github_url -> class_type
    unknown: list[str] = field(default_factory=list)


# ── JSON Preprocessing ─────────────────────────────────────────────────────────


def preprocess_json(text: str) -> str:
    """
    Strip n8n template expressions ({{ ... }}) that may be embedded in
    ComfyUI API JSONs when workflows are called from n8n.

    Two cases:
      "{{expression}}"  → "n8n_expr"   (quoted in JSON string)
      {{expression}}    → null          (bare JSON value)
    """
    text = re.sub(r'"{{[^}]*}}"', '"n8n_expr"', text)
    text = re.sub(r"{{[^}]*}}", "null", text)
    return text


# ── Workflow Parsing ───────────────────────────────────────────────────────────


def extract_node_types_gui(wf: dict) -> set[str]:
    """Extract class types from ComfyUI GUI format (has nodes[] array)."""
    types: set[str] = set()
    for node in wf.get("nodes", []):
        ntype = node.get("type")
        if ntype:
            types.add(ntype)
    return types


def extract_node_types_api(wf: dict) -> set[str]:
    """Extract class types from ComfyUI API format ({nodeId: {class_type, inputs}})."""
    types: set[str] = set()
    for val in wf.values():
        if isinstance(val, dict) and "class_type" in val:
            types.add(val["class_type"])
    return types


def scan_workflows(workflows_dir: Path) -> dict[str, list[str]]:
    """
    Scan all ComfyUI JSON workflows in a directory.
    Returns {class_type: [filename, ...]} for every unique class_type found.
    """
    type_to_files: dict[str, list[str]] = {}

    for json_file in sorted(workflows_dir.glob("*.json")):
        raw = json_file.read_text(encoding="utf-8")
        try:
            wf = json.loads(raw)
        except json.JSONDecodeError:
            try:
                wf = json.loads(preprocess_json(raw))
            except json.JSONDecodeError:
                continue

        if "nodes" in wf:
            types = extract_node_types_gui(wf)
        else:
            types = extract_node_types_api(wf)

        for t in types:
            type_to_files.setdefault(t, []).append(json_file.name)

    return type_to_files


# ── Core Node Discovery ───────────────────────────────────────────────────────


def scan_core_comfyui_nodes(comfyui_dir: Path) -> set[str]:
    """
    Dynamically find all class_types defined in core ComfyUI Python files
    (everything outside custom_nodes/).
    Handles both the old NODE_CLASS_MAPPINGS API and the new io.ComfyNode API.
    """
    core_types: set[str] = set()
    skip_dirs = {
        "custom_nodes", "__pycache__", ".git", "web",
        "output", "input", "temp", "models", "user",
    }

    old_pattern = re.compile(r"""[\"']([A-Za-z][\w: ]+)[\"']\s*:""")
    new_pattern = re.compile(r"""node_id\s*=\s*[\"']([A-Za-z][\w: ]+)[\"']""")

    for root, dirs, files in os.walk(comfyui_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            try:
                content = open(fpath, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for m in old_pattern.finditer(content):
                core_types.add(m.group(1))
            for m in new_pattern.finditer(content):
                core_types.add(m.group(1))

    return core_types


# ── Extension Map ──────────────────────────────────────────────────────────────


def load_extension_node_map(comfyui_dir: Path) -> dict[str, str]:
    """
    Load ComfyUI Manager's extension-node-map.json if present.
    Returns {class_type: github_url}.
    """
    map_path = comfyui_dir / "custom_nodes" / "comfyui-manager" / "extension-node-map.json"
    if not map_path.exists():
        return {}

    data = json.loads(map_path.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for repo_url, val in data.items():
        if isinstance(val, list) and val and isinstance(val[0], list):
            for class_type in val[0]:
                if class_type not in result:
                    result[class_type] = repo_url
    return result


# ── Installation Checking ──────────────────────────────────────────────────────


def get_installed_folders(comfyui_dir: Path) -> dict[str, str]:
    """
    Scan custom_nodes/ and return:
      {folder_name_lower: remote_url_lower}

    remote_url is read from .git/config when available; otherwise empty.
    Keys are lowercased for case-insensitive comparison.
    """
    cn_dir = comfyui_dir / "custom_nodes"
    installed: dict[str, str] = {}
    if not cn_dir.exists():
        return installed

    for folder in cn_dir.iterdir():
        if not folder.is_dir():
            continue
        git_config = folder / ".git" / "config"
        remote_url = ""
        if git_config.exists():
            cfg_text = git_config.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"url\s*=\s*(.+)", cfg_text)
            if m:
                remote_url = m.group(1).strip().removesuffix(".git").rstrip("/")
        installed[folder.name.lower()] = remote_url.lower()

    return installed


def is_repo_installed(github_url: str, installed: dict[str, str]) -> bool:
    """
    Check if a GitHub repo is installed in custom_nodes/.
    Tries:
      1. Remote URL match (case-insensitive, ignores .git suffix)
      2. Folder name derived from GitHub URL (case-insensitive)
    """
    url_norm = github_url.lower().removesuffix(".git").rstrip("/")

    if url_norm in installed.values():
        return True

    folder_guess = url_norm.split("/")[-1]
    return folder_guess in installed


def scan_custom_nodes_for_type(comfyui_dir: Path, class_type: str) -> str | None:
    """
    Fallback: scan Python files in custom_nodes/ to find which folder
    registers the given class_type. Returns folder name or None.
    """
    cn_dir = comfyui_dir / "custom_nodes"
    if not cn_dir.exists():
        return None

    old_pat = re.compile(r"""[\"']""" + re.escape(class_type) + r"""[\"']""")
    new_pat = re.compile(r"node_id\s*=\s*[\"']" + re.escape(class_type) + r"[\"']")

    for folder in sorted(cn_dir.iterdir()):
        if not folder.is_dir() or folder.name.startswith("__"):
            continue
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                try:
                    content = open(
                        os.path.join(root, fname), encoding="utf-8", errors="ignore"
                    ).read()
                except OSError:
                    continue
                if old_pat.search(content) or new_pat.search(content):
                    return folder.name
    return None


# ── Installation ───────────────────────────────────────────────────────────────


def install_via_manager(github_url: str, manager_url: str) -> bool:
    """Attempt to install a custom node via ComfyUI Manager REST API."""
    payload = json.dumps({"id": github_url}).encode("utf-8")
    req = urllib.request.Request(
        manager_url.rstrip("/") + "/customnode/install",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status < 300
    except Exception:
        return False


def install_via_git(github_url: str, comfyui_dir: Path) -> bool:
    """Clone a GitHub repo into custom_nodes/."""
    cn_dir = comfyui_dir / "custom_nodes"
    result = subprocess.run(
        ["git", "clone", github_url],
        cwd=str(cn_dir),
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


# ── Full Scan ──────────────────────────────────────────────────────────────────


def scan(
    workflows_dir: Path,
    comfyui_dir: Path,
) -> ScanResult:
    """
    Perform a full scan: parse workflows, classify nodes, check installation.
    Returns a ScanResult with all findings.
    """
    result = ScanResult()

    # Scan workflows
    result.type_to_files = scan_workflows(workflows_dir)
    result.total_workflows = len(list(workflows_dir.glob("*.json")))
    result.total_class_types = len(result.type_to_files)

    # Scan core nodes
    core_nodes = scan_core_comfyui_nodes(comfyui_dir)

    # Classify
    for t in result.type_to_files:
        if UUID_PATTERN.match(t):
            result.uuid_types.add(t)
        elif t in FRONTEND_ONLY_NODES:
            result.frontend_types.add(t)
        elif t in core_nodes:
            result.core_types.add(t)
        else:
            result.custom_types.add(t)

    result.uuid_count = len(result.uuid_types)
    result.frontend_count = len(result.frontend_types)
    result.core_count = len(result.core_types)
    result.custom_count = len(result.custom_types)

    if not result.custom_types:
        return result

    # Load extension map and installed folders
    ext_map = load_extension_node_map(comfyui_dir)
    installed = get_installed_folders(comfyui_dir)

    # Check each custom type
    for class_type in sorted(result.custom_types):
        github_url = ext_map.get(class_type)

        if github_url:
            inst = is_repo_installed(github_url, installed)
            if not inst:
                found_folder = scan_custom_nodes_for_type(comfyui_dir, class_type)
                if found_folder:
                    inst = True
            if inst:
                result.installed.append(class_type)
            else:
                result.missing.setdefault(github_url, class_type)
        else:
            found_folder = scan_custom_nodes_for_type(comfyui_dir, class_type)
            if found_folder:
                result.installed.append(class_type)
            else:
                result.unknown.append(class_type)

    return result
