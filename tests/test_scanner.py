"""Tests for comfyui_dependency_scanner.scanner."""

import json
import os
from pathlib import Path

import pytest

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


# ── preprocess_json ────────────────────────────────────────────────────────────


class TestPreprocessJson:
    def test_strips_quoted_template_expressions(self):
        text = '{\"key\": \"{{$json.value}}\"}'
        result = preprocess_json(text)
        assert result == '{\"key\": \"n8n_expr\"}'

    def test_strips_bare_template_expressions(self):
        text = '{\"key\": {{$json.value}}}'
        result = preprocess_json(text)
        assert result == '{\"key\": null}'

    def test_leaves_normal_json_untouched(self):
        text = '{\"key\": \"value\", \"num\": 42}'
        assert preprocess_json(text) == text

    def test_multiple_expressions(self):
        text = '{\"a\": \"{{expr1}}\", \"b\": {{expr2}}}'
        result = preprocess_json(text)
        assert "{{" not in result
        assert "n8n_expr" in result


# ── extract_node_types ─────────────────────────────────────────────────────────


class TestExtractNodeTypes:
    def test_gui_format(self):
        wf = {
            "nodes": [
                {"type": "KSampler", "id": 1},
                {"type": "VAEDecode", "id": 2},
                {"type": "KSampler", "id": 3},  # duplicate
            ]
        }
        types = extract_node_types_gui(wf)
        assert types == {"KSampler", "VAEDecode"}

    def test_gui_format_no_type(self):
        wf = {"nodes": [{"id": 1}]}
        types = extract_node_types_gui(wf)
        assert types == set()

    def test_gui_format_empty_nodes(self):
        wf = {"nodes": []}
        types = extract_node_types_gui(wf)
        assert types == set()

    def test_gui_format_no_nodes_key(self):
        wf = {"other": "value"}
        types = extract_node_types_gui(wf)
        assert types == set()

    def test_api_format(self):
        wf = {
            "1": {"class_type": "KSampler", "inputs": {}},
            "2": {"class_type": "VAEDecode", "inputs": {}},
        }
        types = extract_node_types_api(wf)
        assert types == {"KSampler", "VAEDecode"}

    def test_api_format_mixed_values(self):
        wf = {
            "1": {"class_type": "KSampler", "inputs": {}},
            "extra_data": {"some_field": "value"},  # no class_type
        }
        types = extract_node_types_api(wf)
        assert types == {"KSampler"}

    def test_api_format_non_dict_values(self):
        wf = {
            "1": {"class_type": "KSampler", "inputs": {}},
            "2": "string_value",
        }
        types = extract_node_types_api(wf)
        assert types == {"KSampler"}


# ── UUID and frontend detection ────────────────────────────────────────────────


class TestNodeClassification:
    def test_uuid_pattern_matches(self):
        assert UUID_PATTERN.match("12345678-1234-4123-9123-123456789abc")

    def test_uuid_pattern_case_insensitive(self):
        assert UUID_PATTERN.match("12345678-1234-4123-9123-123456789ABC")

    def test_uuid_pattern_rejects_normal_types(self):
        assert not UUID_PATTERN.match("KSampler")
        assert not UUID_PATTERN.match("VAEDecode")

    def test_uuid_pattern_rejects_malformed(self):
        assert not UUID_PATTERN.match("12345678-1234-4123-9123-12345678")  # too short
        assert not UUID_PATTERN.match("12345678-1234-4123-9123-123456789abc-extra")

    def test_frontend_only_nodes_not_empty(self):
        assert len(FRONTEND_ONLY_NODES) > 0

    def test_frontend_only_nodes_includes_markdown(self):
        assert "MarkdownNote" in FRONTEND_ONLY_NODES


# ── scan_workflows ─────────────────────────────────────────────────────────────


class TestScanWorkflows:
    def test_scans_gui_workflow(self, tmp_path):
        wf = {
            "nodes": [
                {"type": "KSampler", "id": 1},
                {"type": "CustomNode", "id": 2},
            ]
        }
        (tmp_path / "test.json").write_text(json.dumps(wf))
        result = scan_workflows(tmp_path)
        assert "KSampler" in result
        assert "CustomNode" in result
        assert result["KSampler"] == ["test.json"]

    def test_scans_api_workflow(self, tmp_path):
        wf = {
            "1": {"class_type": "CLIPLoader", "inputs": {}},
        }
        (tmp_path / "api.json").write_text(json.dumps(wf))
        result = scan_workflows(tmp_path)
        assert "CLIPLoader" in result

    def test_handles_n8n_template_expressions(self, tmp_path):
        raw = '{\"1\": {\"class_type\": \"LoadImage\", \"inputs\": {\"image\": \"{{$json.path}}\"}}}'
        (tmp_path / "n8n.json").write_text(raw)
        result = scan_workflows(tmp_path)
        assert "LoadImage" in result

    def test_empty_directory(self, tmp_path):
        result = scan_workflows(tmp_path)
        assert result == {}

    def test_invalid_json_skipped(self, tmp_path):
        (tmp_path / "bad.json").write_text("not json at all")
        result = scan_workflows(tmp_path)
        assert result == {}

    def test_multiple_workflows_merge(self, tmp_path):
        wf1 = {"nodes": [{"type": "KSampler", "id": 1}]}
        wf2 = {"nodes": [{"type": "KSampler", "id": 1}, {"type": "VAEDecode", "id": 2}]}
        (tmp_path / "a.json").write_text(json.dumps(wf1))
        (tmp_path / "b.json").write_text(json.dumps(wf2))
        result = scan_workflows(tmp_path)
        assert set(result["KSampler"]) == {"a.json", "b.json"}
        assert result["VAEDecode"] == ["b.json"]

    def test_ignores_non_json_files(self, tmp_path):
        (tmp_path / "readme.txt").write_text("not a json file")
        (tmp_path / "script.py").write_text("import json")
        result = scan_workflows(tmp_path)
        assert result == {}

    def test_mixed_gui_and_api_formats(self, tmp_path):
        gui_wf = {"nodes": [{"type": "KSampler", "id": 1}]}
        api_wf = {"1": {"class_type": "VAEDecode", "inputs": {}}}
        (tmp_path / "gui.json").write_text(json.dumps(gui_wf))
        (tmp_path / "api.json").write_text(json.dumps(api_wf))
        result = scan_workflows(tmp_path)
        assert "KSampler" in result
        assert "VAEDecode" in result


# ── scan_core_comfyui_nodes ────────────────────────────────────────────────────


class TestScanCoreComfyuiNodes:
    def test_scans_core_nodes_old_api(self, tmp_path):
        # Create a mock ComfyUI directory with a Python file using old NODE_CLASS_MAPPINGS API
        (tmp_path / "nodes.py").write_text(
            '''
NODE_CLASS_MAPPINGS = {
    "KSampler": KSamplerClass,
    "VAEDecode": VAEDecodeClass,
}
'''
        )
        result = scan_core_comfyui_nodes(tmp_path)
        assert "KSampler" in result
        assert "VAEDecode" in result

    def test_scans_core_nodes_new_api(self, tmp_path):
        # Create a mock ComfyUI directory with a Python file using new io.ComfyNode API
        (tmp_path / "nodes.py").write_text(
            '''
class MyNode(ComfyNode):
    node_id = "MyCustomNode"
'''
        )
        result = scan_core_comfyui_nodes(tmp_path)
        assert "MyCustomNode" in result

    def test_skips_custom_nodes_directory(self, tmp_path):
        # Core nodes scanning should skip custom_nodes/
        (tmp_path / "core.py").write_text('NODE_CLASS_MAPPINGS = {"CoreNode": CoreNodeClass}')
        cn_dir = tmp_path / "custom_nodes"
        cn_dir.mkdir()
        (cn_dir / "plugin.py").write_text(
            'NODE_CLASS_MAPPINGS = {"PluginNode": PluginNodeClass}'
        )
        result = scan_core_comfyui_nodes(tmp_path)
        assert "CoreNode" in result
        assert "PluginNode" not in result

    def test_empty_directory(self, tmp_path):
        result = scan_core_comfyui_nodes(tmp_path)
        assert result == set()

    def test_handles_malformed_python_files(self, tmp_path):
        (tmp_path / "broken.py").write_text("def func(:\n  pass  # syntax error")
        # Should not crash
        result = scan_core_comfyui_nodes(tmp_path)
        assert isinstance(result, set)


# ── get_installed_folders ──────────────────────────────────────────────────────


class TestGetInstalledFolders:
    def test_no_custom_nodes_directory(self, tmp_path):
        result = get_installed_folders(tmp_path)
        assert result == {}

    def test_empty_custom_nodes(self, tmp_path):
        cn_dir = tmp_path / "custom_nodes"
        cn_dir.mkdir()
        result = get_installed_folders(tmp_path)
        assert result == {}

    def test_folder_without_git(self, tmp_path):
        cn_dir = tmp_path / "custom_nodes"
        cn_dir.mkdir()
        (cn_dir / "my_plugin").mkdir()
        result = get_installed_folders(tmp_path)
        assert "my_plugin" in result
        assert result["my_plugin"] == ""

    def test_folder_with_git_remote(self, tmp_path):
        cn_dir = tmp_path / "custom_nodes"
        cn_dir.mkdir()
        plugin_dir = cn_dir / "my_plugin"
        plugin_dir.mkdir()
        git_dir = plugin_dir / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("[remote \"origin\"]\n    url = https://github.com/user/my-plugin.git\n")
        result = get_installed_folders(tmp_path)
        assert "my_plugin" in result
        assert "github.com/user/my-plugin" in result["my_plugin"]

    def test_case_insensitive_keys(self, tmp_path):
        cn_dir = tmp_path / "custom_nodes"
        cn_dir.mkdir()
        (cn_dir / "MyPlugin").mkdir()
        result = get_installed_folders(tmp_path)
        assert "myplugin" in result

    def test_handles_git_config_without_url(self, tmp_path):
        cn_dir = tmp_path / "custom_nodes"
        cn_dir.mkdir()
        plugin_dir = cn_dir / "my_plugin"
        plugin_dir.mkdir()
        git_dir = plugin_dir / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("[core]\n    bare = false\n")
        result = get_installed_folders(tmp_path)
        assert result["my_plugin"] == ""


# ── is_repo_installed ──────────────────────────────────────────────────────────


class TestIsRepoInstalled:
    def test_matches_by_remote_url(self):
        installed = {"my_plugin": "https://github.com/user/my-plugin"}
        assert is_repo_installed("https://github.com/user/my-plugin.git", installed)

    def test_matches_by_folder_name(self):
        installed = {"my-plugin": ""}
        assert is_repo_installed("https://github.com/user/my-plugin.git", installed)

    def test_case_insensitive_matching(self):
        installed = {"myplugin": ""}
        assert is_repo_installed("https://github.com/user/MyPlugin.git", installed)

    def test_not_installed(self):
        installed = {"other_plugin": ""}
        assert not is_repo_installed("https://github.com/user/my-plugin.git", installed)

    def test_empty_installed_dict(self):
        assert not is_repo_installed("https://github.com/user/my-plugin.git", {})


# ── load_extension_node_map ────────────────────────────────────────────────────


class TestLoadExtensionNodeMap:
    def test_no_map_file(self, tmp_path):
        result = load_extension_node_map(tmp_path)
        assert result == {}

    def test_loads_valid_map(self, tmp_path):
        cn_dir = tmp_path / "custom_nodes"
        manager_dir = cn_dir / "comfyui-manager"
        manager_dir.mkdir(parents=True)
        map_data = {
            "https://github.com/user/plugin1.git": [["Node1", "Node2"]],
            "https://github.com/user/plugin2.git": [["Node3"]],
        }
        (manager_dir / "extension-node-map.json").write_text(json.dumps(map_data))
        result = load_extension_node_map(tmp_path)
        assert result["Node1"] == "https://github.com/user/plugin1.git"
        assert result["Node2"] == "https://github.com/user/plugin1.git"
        assert result["Node3"] == "https://github.com/user/plugin2.git"

    def test_skips_duplicates_first_wins(self, tmp_path):
        cn_dir = tmp_path / "custom_nodes"
        manager_dir = cn_dir / "comfyui-manager"
        manager_dir.mkdir(parents=True)
        map_data = {
            "https://github.com/user/plugin1.git": [["SharedNode"]],
            "https://github.com/user/plugin2.git": [["SharedNode"]],
        }
        (manager_dir / "extension-node-map.json").write_text(json.dumps(map_data))
        result = load_extension_node_map(tmp_path)
        # First URL wins
        assert result["SharedNode"] == "https://github.com/user/plugin1.git"


# ── scan_custom_nodes_for_type ─────────────────────────────────────────────────


class TestScanCustomNodesForType:
    def test_finds_node_by_old_api(self, tmp_path):
        cn_dir = tmp_path / "custom_nodes"
        plugin_dir = cn_dir / "my_plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "nodes.py").write_text(
            'NODE_CLASS_MAPPINGS = {"CustomType": CustomClass}'
        )
        result = scan_custom_nodes_for_type(tmp_path, "CustomType")
        assert result == "my_plugin"

    def test_finds_node_by_new_api(self, tmp_path):
        cn_dir = tmp_path / "custom_nodes"
        plugin_dir = cn_dir / "my_plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "nodes.py").write_text('node_id = "CustomType"')
        result = scan_custom_nodes_for_type(tmp_path, "CustomType")
        assert result == "my_plugin"

    def test_not_found(self, tmp_path):
        cn_dir = tmp_path / "custom_nodes"
        plugin_dir = cn_dir / "my_plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "nodes.py").write_text('NODE_CLASS_MAPPINGS = {"OtherType": OtherClass}')
        result = scan_custom_nodes_for_type(tmp_path, "MissingType")
        assert result is None

    def test_no_custom_nodes_dir(self, tmp_path):
        result = scan_custom_nodes_for_type(tmp_path, "AnyType")
        assert result is None


# ── scan (full integration test) ───────────────────────────────────────────────


class TestScan:
    def test_scan_returns_scan_result(self, tmp_path):
        # Create workflows dir
        wf_dir = tmp_path / "workflows"
        wf_dir.mkdir()
        wf = {"nodes": [{"type": "KSampler", "id": 1}]}
        (wf_dir / "test.json").write_text(json.dumps(wf))

        # Create ComfyUI dir
        comfyui_dir = tmp_path / "comfyui"
        comfyui_dir.mkdir()
        (comfyui_dir / "nodes.py").write_text('NODE_CLASS_MAPPINGS = {"KSampler": KSamplerClass}')

        result = scan(wf_dir, comfyui_dir)

        assert isinstance(result, ScanResult)
        assert result.total_workflows == 1
        assert result.core_count == 1
        assert "KSampler" in result.core_types

    def test_scan_classifies_custom_nodes(self, tmp_path):
        # Create workflows dir with custom node
        wf_dir = tmp_path / "workflows"
        wf_dir.mkdir()
        wf = {"nodes": [{"type": "CustomType", "id": 1}]}
        (wf_dir / "test.json").write_text(json.dumps(wf))

        # Create ComfyUI dir
        comfyui_dir = tmp_path / "comfyui"
        comfyui_dir.mkdir()

        result = scan(wf_dir, comfyui_dir)

        assert result.custom_count == 1
        assert "CustomType" in result.custom_types

    def test_scan_identifies_uuid_nodes(self, tmp_path):
        # Create workflows dir with UUID node
        wf_dir = tmp_path / "workflows"
        wf_dir.mkdir()
        uuid_node = "12345678-1234-4123-9123-123456789abc"
        wf = {"nodes": [{"type": uuid_node, "id": 1}]}
        (wf_dir / "test.json").write_text(json.dumps(wf))

        # Create ComfyUI dir
        comfyui_dir = tmp_path / "comfyui"
        comfyui_dir.mkdir()

        result = scan(wf_dir, comfyui_dir)

        assert result.uuid_count == 1
        assert uuid_node in result.uuid_types

    def test_scan_identifies_frontend_nodes(self, tmp_path):
        # Create workflows dir with frontend node
        wf_dir = tmp_path / "workflows"
        wf_dir.mkdir()
        wf = {"nodes": [{"type": "MarkdownNote", "id": 1}]}
        (wf_dir / "test.json").write_text(json.dumps(wf))

        # Create ComfyUI dir
        comfyui_dir = tmp_path / "comfyui"
        comfyui_dir.mkdir()

        result = scan(wf_dir, comfyui_dir)

        assert result.frontend_count == 1
        assert "MarkdownNote" in result.frontend_types

    def test_scan_marks_installed_custom_node(self, tmp_path):
        # Create workflows dir
        wf_dir = tmp_path / "workflows"
        wf_dir.mkdir()
        wf = {"nodes": [{"type": "CustomType", "id": 1}]}
        (wf_dir / "test.json").write_text(json.dumps(wf))

        # Create ComfyUI dir with extension map
        comfyui_dir = tmp_path / "comfyui"
        comfyui_dir.mkdir()
        cn_dir = comfyui_dir / "custom_nodes"
        cn_dir.mkdir()

        # Create manager extension map
        manager_dir = cn_dir / "comfyui-manager"
        manager_dir.mkdir()
        map_data = {"https://github.com/user/custom-type.git": [["CustomType"]]}
        (manager_dir / "extension-node-map.json").write_text(json.dumps(map_data))

        # Create the actual plugin folder
        plugin_dir = cn_dir / "custom-type"
        plugin_dir.mkdir()

        result = scan(wf_dir, comfyui_dir)

        assert result.custom_count == 1
        assert "CustomType" in result.installed

    def test_scan_marks_missing_custom_node(self, tmp_path):
        # Create workflows dir
        wf_dir = tmp_path / "workflows"
        wf_dir.mkdir()
        wf = {"nodes": [{"type": "CustomType", "id": 1}]}
        (wf_dir / "test.json").write_text(json.dumps(wf))

        # Create ComfyUI dir with extension map
        comfyui_dir = tmp_path / "comfyui"
        comfyui_dir.mkdir()
        cn_dir = comfyui_dir / "custom_nodes"
        cn_dir.mkdir()

        # Create manager extension map (but NOT the actual plugin)
        manager_dir = cn_dir / "comfyui-manager"
        manager_dir.mkdir()
        map_data = {"https://github.com/user/custom-type.git": [["CustomType"]]}
        (manager_dir / "extension-node-map.json").write_text(json.dumps(map_data))

        result = scan(wf_dir, comfyui_dir)

        assert result.custom_count == 1
        assert "CustomType" in result.unknown or "CustomType" not in result.installed

    def test_scan_marks_unknown_custom_node(self, tmp_path):
        # Create workflows dir with unknown custom node
        wf_dir = tmp_path / "workflows"
        wf_dir.mkdir()
        wf = {"nodes": [{"type": "UnknownType", "id": 1}]}
        (wf_dir / "test.json").write_text(json.dumps(wf))

        # Create ComfyUI dir (no extension map)
        comfyui_dir = tmp_path / "comfyui"
        comfyui_dir.mkdir()
        cn_dir = comfyui_dir / "custom_nodes"
        cn_dir.mkdir()

        result = scan(wf_dir, comfyui_dir)

        assert result.custom_count == 1
        assert "UnknownType" in result.unknown
