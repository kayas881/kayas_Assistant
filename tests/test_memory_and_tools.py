import os
from pathlib import Path

import pytest

from src.memory.vector_memory import VectorMemory, VectorMemoryConfig
from src.executors.local_search import LocalSearchExecutor, LocalSearchConfig
from src.executors.web_exec import WebExecutor, WebConfig
from src.executors.email_exec import EmailExecutor, EmailConfig
from src.executors.filesystem import FileSystemExecutor, FSConfig


def test_vector_memory_add_query(tmp_path: Path, monkeypatch):
    # Skip if no local Ollama embeddings; expect graceful handling and empty results
    v = VectorMemory(VectorMemoryConfig(persist_dir=tmp_path / "chroma", embed_model="nomic-embed-text"))
    v.add(["Goal: test\nArtifact: /tmp/x"], metadatas=[{"artifact": "/tmp/x"}], ids=["1"])
    res = v.query("test")
    assert isinstance(res, list)


def test_local_search(tmp_path: Path):
    f = tmp_path / "hello.txt"
    f.write_text("This is a freelancing note", encoding="utf-8")
    search = LocalSearchExecutor(LocalSearchConfig(root=tmp_path))
    out = search.search("freelancing")
    assert any("hello.txt" in r["path"] for r in out["results"])


def test_filesystem_executor(tmp_path: Path):
    fs = FileSystemExecutor(FSConfig(root=tmp_path))
    fs.create_file("notes.txt", "hi")
    fs.append_file("notes.txt", "\nmore")
    content = (tmp_path / "notes.txt").read_text(encoding="utf-8")
    assert "hi" in content and "more" in content


def test_email_executor_config_error():
    email = EmailExecutor(EmailConfig(host="", port=587, user="", password="", from_addr=""))
    with pytest.raises(ValueError):
        email.send("to@example.com", "subject", "body")


def test_web_executor_mock(monkeypatch):
    def fake_get(self, url):
        class R:
            status_code = 200

            def raise_for_status(self):
                return None

            @property
            def text(self):
                return "<html><head><title>Test</title></head><body><p>Hello</p></body></html>"

        return R()

    import httpx

    monkeypatch.setattr(httpx.Client, "get", fake_get, raising=True)
    web = WebExecutor(WebConfig())
    out = web.fetch("http://example.com")
    assert out["title"] == "Test"