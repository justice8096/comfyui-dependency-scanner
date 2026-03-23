"""Tests for comfyui_dependency_scanner.scanner."""

import json
import os
from pathlib import Path

import pytest

from comfyui_dependency_scanner.scanner import (
    FRONTEND_ONLY_NODES,
    UUID_PATTERN,
    extract_node_types_api,
    extract_node_types_gui,
    preprocess_json,
    scan_workflows,
    type_to_package,
)


# ── preprocess_json ────────────────────────────────────────────────────────────


class TestPreprocessJson:
    def test_strips_quoted_template_expressions(self):
        text = '{"key": "{{$json.value}}"}'
        result = preprocess_json(text)
        assert result == '{"key": "n8n_expr"}'

    def test_strips_bare_template_expressions(self):
        text = '{"key": {{$json.value}}}'
        result = preprocess_json(text)
        assert result == '{"key": null}'

    def test_leaves_normal_json_untouched(self):
        text = '{"key": "value", "num": 42}'
        assert preprocess_json(text) == text


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


# ── UUID and frontend detection ────────────────────────────────────────────────


class TestNodeClassification:
    def test_uuid_pattern_matches(self):
        assert UUID_PATTERN.match("12345678-1234-4123-9123-123456789abc")

    def test_uuid_pattern_rejects_normal_types(self):
        assert not UUID_PATTERN.match("KSampler")
        assert not UUID_PATTERN.match("VAEDecode")

    def test_frontend_only_nodes(self):
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
        raw = '{"1": {"class_type": "LoadImage", "inputs": {"image": "{{$json.path}}"}}}'
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
