#!/usr/bin/env python3
"""
CLI entry point for comfyui-dependency-scanner.

Usage:
    comfyui-scan <workflows-dir> <comfyui-dir>                  # check only
    comfyui-scan <workflows-dir> <comfyui-dir> --install        # check + install
    comfyui-scan <workflows-dir> <comfyui-dir> --json           # machine-readable output
    comfyui-scan --help
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .scanner import (
    install_via_git,
    install_via_manager,
    scan,
)

MANAGER_API_URL = "http://127.0.0.1:8188"


def print_usage() -> None:
    print(
        """comfyui-scan — ComfyUI Workflow Dependency Scanner

Usage:
    comfyui-scan <workflows-dir> <comfyui-dir> [options]

Arguments:
    workflows-dir   Directory containing ComfyUI workflow JSON files
    comfyui-dir     Path to the ComfyUI installation (contains custom_nodes/)

Options:
    --install       Install missing custom node packages automatically
    --manager-url   ComfyUI Manager API URL (default: http://127.0.0.1:8188)
    --json          Output results as JSON (for scripting/CI)
    --help          Show this help message
"""
    )


def main() -> None:
    args = sys.argv[1:]

    # Parse flags
    do_install = "--install" in args
    output_json = "--json" in args
    show_help = "--help" in args or "-h" in args

    if show_help:
        print_usage()
        sys.exit(0)

    known_flags = {"--install", "--json", "--help", "-h"}
    manager_url = MANAGER_API_URL
    positional: list[str] = []

    i = 0
    while i < len(args):
        if args[i] == "--manager-url" and i + 1 < len(args):
            manager_url = args[i + 1]
            i += 2
        elif args[i] in known_flags:
            i += 1
        elif args[i].startswith("--"):
            print(f"WARNING: Unknown flag '{args[i]}' (ignored)")
            i += 1
        else:
            positional.append(args[i])
            i += 1

    if len(positional) < 2:
        print("ERROR: Both <workflows-dir> and <comfyui-dir> are required.\n")
        print_usage()
        sys.exit(1)

    workflows_dir = Path(positional[0])
    comfyui_dir = Path(positional[1])

    if not workflows_dir.exists():
        print(f"ERROR: Workflows directory not found: {workflows_dir}")
        sys.exit(1)
    if not comfyui_dir.exists():
        print(f"ERROR: ComfyUI directory not found: {comfyui_dir}")
        sys.exit(1)

    # Run scan
    result = scan(workflows_dir, comfyui_dir)

    # JSON output
    if output_json:
        output = {
            "total_workflows": result.total_workflows,
            "total_class_types": result.total_class_types,
            "core_count": result.core_count,
            "custom_count": result.custom_count,
            "uuid_count": result.uuid_count,
            "frontend_count": result.frontend_count,
            "installed": result.installed,
            "missing": result.missing,
            "unknown": result.unknown,
        }
        print(json.dumps(output, indent=2))
        if result.missing or result.unknown:
            sys.exit(1)
        sys.exit(0)

    # Human-readable output
    print("=" * 64)
    print("ComfyUI Workflow Dependency Scanner")
    print("=" * 64)
    print(f"Workflows dir : {workflows_dir}")
    print(f"ComfyUI dir   : {comfyui_dir}")
    print(f"Mode          : {'CHECK + INSTALL' if do_install else 'CHECK ONLY'}")
    print()
    print(
        f"Found {result.total_class_types} unique class_type(s) "
        f"across {result.total_workflows} workflow(s)."
    )
    print()

    if result.uuid_count:
        print(f"  Skipping {result.uuid_count} UUID proxy widget node(s).")
    if result.frontend_count:
        print(
            f"  Skipping {result.frontend_count} frontend-only node(s): "
            f"{', '.join(sorted(result.frontend_types))}"
        )
    print(f"  Core ComfyUI nodes : {result.core_count}")
    print(f"  Custom nodes       : {result.custom_count}")
    print()

    if not result.custom_types:
        print("All node types are built into ComfyUI — no custom packages needed.")
        sys.exit(0)

    # Show installed
    for ct in result.installed:
        print(f"  [OK] {ct}")
        files = result.type_to_files.get(ct, [])
        if files:
            print(f"       used in : {', '.join(sorted(files))}")

    # Show missing
    for url, ct in result.missing.items():
        print(f"  [!!] {ct}")
        print(f"       package : {url}")
        files = result.type_to_files.get(ct, [])
        if files:
            print(f"       used in : {', '.join(sorted(files))}")

    # Show unknown
    for ct in result.unknown:
        print(f"  [??] {ct}")
        print(f"       package : UNKNOWN — not in ComfyUI Manager registry")
        files = result.type_to_files.get(ct, [])
        if files:
            print(f"       used in : {', '.join(sorted(files))}")

    print()

    if result.unknown:
        print(f"WARN: {len(result.unknown)} node type(s) not found anywhere:")
        for t in result.unknown:
            print(f"  - {t}")
        print()

    if not result.missing:
        print("All identified custom packages are installed.")
        sys.exit(0 if not result.unknown else 2)

    print(f"Missing package(s) ({len(result.missing)}):")
    for url in sorted(result.missing):
        print(f"  - {url}")
    print()

    if not do_install:
        print("Run with --install to install them automatically.")
        sys.exit(1)

    # Install
    import urllib.request

    manager_api_reachable = False
    try:
        with urllib.request.urlopen(manager_url + "/manager/version", timeout=3):
            manager_api_reachable = True
    except Exception:
        pass

    if manager_api_reachable:
        print("ComfyUI Manager API is reachable — installing via Manager ...")
    else:
        print("ComfyUI Manager API not reachable — falling back to git clone ...")

    failed: list[str] = []
    for url in sorted(result.missing):
        print(f"\n  Installing: {url}")
        ok = False
        if manager_api_reachable:
            ok = install_via_manager(url, manager_url)
            if ok:
                print("    Manager install queued.")
            else:
                print("    Manager install failed — trying git clone ...")
        if not ok:
            ok = install_via_git(url, comfyui_dir)
            if ok:
                print("    git clone succeeded.")
            else:
                print("    git clone failed.")
        if not ok:
            failed.append(url)

    print()
    if failed:
        print(f"ERROR: {len(failed)} package(s) failed to install:")
        for url in failed:
            print(f"  - {url}")
        sys.exit(1)
    else:
        print("Done. Restart ComfyUI to load the newly installed nodes.")
        sys.exit(0)


if __name__ == "__main__":
    main()
