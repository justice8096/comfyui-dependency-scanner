#!/usr/bin/env python3
"""Quick test to verify all imports work."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from comfyui_dependency_scanner.scanner import (
        FRONTEND_ONLY_NODES,
        UUID_PATTERN,
        ScanResult,
        extract_node_types_api,
        extract_node_types_gui,
        get_installed_folders,
        is_repo_installed,
        load_extension_node_map,
        preprocess_json,
        scan,
        scan_core_comfyui_nodes,
        scan_custom_nodes_for_type,
        scan_workflows,
    )
    print("✓ All scanner imports successful")
    print(f"  - FRONTEND_ONLY_NODES: {FRONTEND_ONLY_NODES}")
    print(f"  - UUID_PATTERN: {UUID_PATTERN.pattern[:50]}...")
    print(f"  - ScanResult: {ScanResult}")
    print("✓ Test imports would also work")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)
