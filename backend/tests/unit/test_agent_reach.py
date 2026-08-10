"""Agent Reach CLI adapter unit tests (roadmap Phase 18)."""

from pathlib import Path

import pytest

from app.osint.agent_reach.capabilities import AgentReachCapabilities
from app.osint.agent_reach.client import AgentReachClient, AgentReachUnavailableError
from app.osint.agent_reach.normalizer import normalize_records
from app.osint.agent_reach.parser import extract_records, parse_json


class FakeCli:
    """Stand-in for the installed agent-reach binary (echoes canned JSON)."""

    def __init__(self, doctor_json, search_json, available=True) -> None:
        self.log = []
        self._doctor = doctor_json
        self._search = search_json
        self.available = available

    def run(self, args):
        self.log.append(args)
        if args[:2] == ["doctor", "--json"]:
            if not self.available:
                raise AgentReachUnavailableError("not installed")
            return self._doctor
        if args[:1] == ["get",]:
            if not self.available:
                raise AgentReachUnavailableError("not installed")
            return self._search
        raise AssertionError(f"unexpected call: {args}")


def _client_with_fake_cli(tmp_path, doctor=None, search=None, available=True):
    fake = FakeCli(doctor or '{"channels": {"web": {"status": "ok"}}}', search or '[{"url": "https://example.com/a"}]', available=available)
    cli = AgentReachClient(cmd=str(tmp_path / "agent-reach"))
    cli.run = fake.run  # type: ignore[assignment]
    cli._cli = str(tmp_path / "agent-reach")
    return cli, fake


def test_client_available_when_cli_present(tmp_path):
    cli, _ = _client_with_fake_cli(tmp_path)
    assert cli.is_available() is True


def test_client_unavailable_when_cli_missing(monkeypatch):
    import app.osint.agent_reach.client as client_mod

    monkeypatch.setattr(client_mod, "_which_cli", lambda candidate: None)
    cli = AgentReachClient(cmd="definitely-missing-binary")
    assert cli.is_available() is False


def test_discover_returns_normalized_candidates(tmp_path):
    cli, _ = _client_with_fake_cli(
        tmp_path,
        search='[{"url": "https://example.com/a", "title": "A", "images": ["https://example.com/i.jpg"]}]',
    )
    candidates = cli.discover("kochi marine")
    assert len(candidates) == 1
    assert candidates[0].url == "https://example.com/a"
    assert candidates[0].title == "A"
    assert candidates[0].images == ["https://example.com/i.jpg"]
    assert candidates[0].kind == "web"


def test_discover_url_query_uses_web_channel(tmp_path):
    cli, fake = _client_with_fake_cli(tmp_path)
    cli.discover("https://example.com/page")
    assert fake.log[-1][:4] == ["get", "web.https://example.com/page", "https://example.com/page", "--json"]


def test_discover_raises_when_cli_missing(monkeypatch, tmp_path):
    import app.osint.agent_reach.client as client_mod

    monkeypatch.setattr(client_mod, "_which_cli", lambda candidate: None)
    cli = AgentReachClient(cmd="missing")
    with pytest.raises(AgentReachUnavailableError):
        cli.discover("kochi")


def test_capabilities_refresh_marks_available(tmp_path):
    cli, _ = _client_with_fake_cli(tmp_path, doctor='{"channels": {"web": {"status": "ok"}, "web2": {"status": "ok"}}}')
    caps = AgentReachCapabilities()
    caps.refresh(cli)
    assert caps.available is True
    assert "web" in caps.sources
    assert "web2" in caps.sources


def test_capabilities_refresh_malformed_marks_unavailable(tmp_path):
    cli, _ = _client_with_fake_cli(tmp_path, doctor="not json")
    caps = AgentReachCapabilities()
    caps.refresh(cli)
    assert caps.available is False
    assert caps.reason


def test_capabilities_refresh_unavailable_cli_marks_unavailable(tmp_path):
    cli, _ = _client_with_fake_cli(tmp_path, available=False)
    caps = AgentReachCapabilities()
    caps.refresh(cli)
    assert caps.available is False
    assert caps.reason


def test_normalizer_drops_records_without_url():
    records = [{"title": "no url"}, {"url": "https://ok.example/x"}]
    candidates = normalize_records(records)
    assert len(candidates) == 1
    assert candidates[0].url == "https://ok.example/x"


def test_normalizer_dedupes():
    records = [{"url": "https://ok.example/x"}, {"url": "https://ok.example/x"}]
    assert len(normalize_records(records)) == 1


def test_parser_extract_records_tolerates_shapes():
    assert extract_records('[{"url": "https://a.example"}]') == [{"url": "https://a.example"}]
    assert extract_records('{"results": [{"url": "https://b.example"}]}') == [{"url": "https://b.example"}]
    assert extract_records("garbage") == []
    with pytest.raises(Exception):
        parse_json("garbage")  # allow_list=False -> raises


def test_parser_json_object_required():
    with pytest.raises(Exception):
        parse_json('["list"]')  # not an object; allow_list default False