import json
from pathlib import Path
from unittest import mock

import pytest

from collectors.schemas import RawDocument
from collectors.cisa_kev import CISAKEVCollector
from collectors.sigma_rules import SigmaRulesCollector
from collectors.atomic_red_team import AtomicRedTeamCollector
from collectors.cisa_advisories import CISAAdvisoryCollector
from collectors.base import BaseCollector


def test_raw_document_schema():
    doc = RawDocument(
        doc_id="test-1",
        source="test",
        source_url="http://test.com",
        title="Test",
        date_collected="2024-01-01T00:00:00",
        content_type="test",
        content_markdown="test content",
        metadata={"key": "value"},
        license="MIT",
        word_count=2
    )
    assert doc.doc_id == "test-1"
    assert doc.word_count == 2


def test_kev_vendor_grouping(tmp_path):
    fixture_path = Path("tests/fixtures/sample_kev_catalog.json")
    collector = CISAKEVCollector({"output_dir": str(tmp_path), "json_url": "file://" + str(fixture_path)})
    
    with mock.patch("requests.get") as mock_get:
        mock_resp = mock.Mock()
        with open(fixture_path, "r", encoding="utf-8") as f:
            mock_resp.json.return_value = json.load(f)
        mock_get.return_value = mock_resp
        
        count = collector.collect(tmp_path)
        
    assert count == 2
    assert collector.doc_count == 2
    
    docs_file = tmp_path / "cisa_kev.jsonl"
    assert docs_file.exists()
    
    with open(docs_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 2
        
        doc1 = json.loads(lines[0])
        doc2 = json.loads(lines[1])
        
        # Checking logic applied in the collector
        assert doc1["metadata"]["vendor"] == "Microsoft"
        assert doc1["metadata"]["ransomware_use_count"] == 1
        assert doc2["metadata"]["vendor"] == "Apache"


def test_sigma_rule_parsing(tmp_path):
    fixture_dir = tmp_path / "rules"
    fixture_dir.mkdir()
    
    with open("tests/fixtures/sample_sigma_rule.yml", "r", encoding="utf-8") as src, open(fixture_dir / "sample.yml", "w", encoding="utf-8") as dst:
        dst.write(src.read())
        
    collector = SigmaRulesCollector({
        "output_dir": str(tmp_path), 
        "clone_dir": str(tmp_path),
        "rules_subdir": "rules"
    })
    
    with mock.patch.object(collector, "_clone_or_pull", return_value=None):
        count = collector.collect(tmp_path)
        
    assert count == 1
    docs_file = tmp_path / "sigma_rules.jsonl"
    with open(docs_file, "r", encoding="utf-8") as f:
        doc = json.loads(f.readline())
        assert doc["doc_id"] == "sigma-5a8a1a36-3a55-4421-b3b3-8b776263bb91"
        assert "T1059.001" in doc["metadata"]["attack_tags"]


def test_atomic_test_parsing(tmp_path):
    fixture_dir = tmp_path / "atomics" / "T1059.001"
    fixture_dir.mkdir(parents=True)
    
    with open("tests/fixtures/sample_atomic_test.yaml", "r", encoding="utf-8") as src, open(fixture_dir / "T1059.001.yaml", "w", encoding="utf-8") as dst:
        dst.write(src.read())
        
    collector = AtomicRedTeamCollector({
        "output_dir": str(tmp_path), 
        "clone_dir": str(tmp_path),
        "atomics_subdir": "atomics"
    })
    
    with mock.patch.object(collector, "_clone_or_pull", return_value=None):
        count = collector.collect(tmp_path)
        
    assert count == 1
    docs_file = tmp_path / "atomic_red_team.jsonl"
    with open(docs_file, "r", encoding="utf-8") as f:
        doc = json.loads(f.readline())
        assert doc["doc_id"] == "art-T1059.001-0"
        assert doc["metadata"]["supported_platforms"] == ["windows"]


def test_cisa_html_extraction(tmp_path):
    collector = CISAAdvisoryCollector({
        "output_dir": str(tmp_path),
        "rss_url": "http://fake.rss",
        "request_delay_seconds": 0.0  # speed up test
    })
    
    rss_content = b"""<?xml version="1.0"?>
    <rss><channel>
        <item>
            <title>Test Advisory</title>
            <link>http://fake.link/AA23-123A</link>
            <pubDate>Mon, 01 Jan 2024</pubDate>
        </item>
    </channel></rss>
    """
    
    with open("tests/fixtures/sample_cisa_advisory.html", "rb") as f:
        html_content = f.read()

    def mock_get(url, *args, **kwargs):
        m = mock.Mock()
        if "rss" in url:
            m.content = rss_content
        else:
            m.content = html_content
        return m
        
    with mock.patch("requests.get", side_effect=mock_get):
        count = collector.collect(tmp_path)
        
    assert count == 1
    docs_file = tmp_path / "cisa_advisories.jsonl"
    with open(docs_file, "r", encoding="utf-8") as f:
        doc = json.loads(f.readline())
        assert "CVE-2023-1234" in doc["metadata"]["cves"]
        assert "T1059.001" in doc["metadata"]["mitre_techniques"]
        assert "192.168.1.1" in doc["metadata"]["iocs"]["ips"]


def test_base_collector_manifest():
    class DummyCollector(BaseCollector):
        SOURCE_URL = "test"
        LICENSE = "test"
        def collect(self, output_dir): pass
        def validate(self, output_dir): return {}
        def manifest(self): return {"test": "ok"}
    
    c = DummyCollector()
    assert c.manifest() == {"test": "ok"}
