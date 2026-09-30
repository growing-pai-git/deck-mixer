"""MCP tool arguments come from a model that may have read untrusted text (an
RFP, a pasted case), so none of them may steer file writes or deletes outside
the case library or the output folder."""

from __future__ import annotations

import importlib
import shutil
from pathlib import Path

import pytest

pytest.importorskip("mcp")

SAMPLE_LIBRARY = Path(__file__).parent.parent / "examples" / "sample-library"

CASE_MD = """---
case_id: test-case
title: A unique test title
client: Zzqx Unrelated Client
status: done
confidentiality: public
---
Body.
"""


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "out"))
    monkeypatch.setenv("LIBRARY_PATH", str(tmp_path / "lib"))
    server = importlib.import_module("deck_mixer.server")
    lib = tmp_path / "lib"
    shutil.copytree(SAMPLE_LIBRARY, lib)
    monkeypatch.setattr(server, "KB_PATH", lib)
    monkeypatch.setattr(server, "OUTPUT_DIR", tmp_path / "out")
    return server


@pytest.fixture
def victim(tmp_path):
    d = tmp_path / "victim"
    d.mkdir()
    (d / "keep.txt").write_text("keep")
    return d


@pytest.mark.parametrize("slug", ["../../victim", "../victim", "..", "/tmp", "a/b", ".hidden"])
def test_remove_case_rejects_paths(server, victim, slug):
    msg = server.remove_case(slug, hard_delete=True)
    assert "Invalid slug" in msg
    assert (victim / "keep.txt").exists()


@pytest.mark.parametrize("slug", ["../../escaped", "/tmp/escaped", "a/b"])
def test_add_case_rejects_paths(server, tmp_path, slug):
    msg = server.add_case(slug, CASE_MD, resolution="add")
    assert "Invalid slug" in msg
    assert not (tmp_path / "escaped").exists()


def test_add_case_rejects_target_slug_paths(server):
    msg = server.add_case("ok", CASE_MD, resolution="replace", target_slug="../../victim")
    assert "Invalid slug" in msg


def test_add_and_remove_case_still_work(server):
    assert "Added new case" in server.add_case("new-case", CASE_MD, resolution="add")
    assert (server.KB_PATH / "cases" / "new-case" / "case.md").exists()
    assert "Archived" in server.remove_case("new-case")
    assert (server.KB_PATH / "_archive" / "new-case").is_dir()


def test_bundled_sample_library_is_read_only(server, monkeypatch):
    monkeypatch.setattr(server, "KB_PATH", server._SAMPLE_LIBRARY)
    assert "sample library" in server.add_case("x", CASE_MD, resolution="add")
    assert "sample library" in server.remove_case("northwind-retail-support")
    assert (server._SAMPLE_LIBRARY / "cases" / "northwind-retail-support").is_dir()


@pytest.mark.parametrize("name", ["../escaped", "/tmp/escaped", "a/b", "..", ".hidden", "a\\b"])
def test_outfile_rejects_paths(server, name):
    assert "Invalid filename" in server._filename_error(name)
    with pytest.raises(ValueError):
        server._outfile("plan", name)


@pytest.mark.parametrize("name", ["Acme tender 2026", "deck_v2.final", "Überblick"])
def test_outfile_accepts_plain_names(server, name):
    assert server._outfile("plan", name) == server.OUTPUT_DIR / f"{name}.pptx"
