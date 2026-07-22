import argparse
import logging
from pathlib import Path
from rich.console import Console
from rich.table import Table

from collectors.mitre_attack import MitreAttackCollector
from collectors.sigma_rules import SigmaRulesCollector
from collectors.atomic_red_team import AtomicRedTeamCollector
from collectors.cisa_advisories import CISAAdvisoriesCollector
from collectors.volatility3_docs import Volatility3DocsCollector
from collectors.mitre_atlas import MitreAtlasCollector
from collectors.cisa_kev import CISAKEVCollector
from collectors.kape_files import KapeFilesCollector
from collectors.hayabusa_rules import HayabusaRulesCollector
from collectors.lolbas_gtfobins import LOLBASGTFOBinsCollector
from collectors.forensic_artifacts import ForensicArtifactsCollector
from collectors.velociraptor_artifacts import VelociraptorArtifactsCollector
from collectors.hijacklibs import HijackLibsCollector
from collectors.loldrivers import LOLDriversCollector
from collectors.ossem_data_dicts import OSSEMDataDictsCollector
from collectors.cybersec_skills import CybersecSkillsCollector
from utils.io import load_yaml, write_json


def load_config(config_path: str) -> dict:
    return load_yaml(config_path, default={})

def write_combined_manifest(results: list[dict], manifest_dir: Path):
    write_json(manifest_dir / "collection_manifest.json", results)

def print_summary_table(results: list[dict]):
    console = Console()
    table = Table(title="Collection Summary")
    table.add_column("Collector", justify="left", style="cyan", no_wrap=True)
    table.add_column("Documents", justify="right", style="magenta")
    table.add_column("Errors", justify="right", style="red")
    table.add_column("Warnings", justify="right", style="yellow")
    table.add_column("Duration (s)", justify="right", style="green")

    total_docs = 0
    for r in results:
        doc_count = r.get("document_count", 0)
        total_docs += doc_count
        table.add_row(
            r.get("collector", "Unknown"),
            str(doc_count),
            str(len(r.get("errors", []))),
            str(len(r.get("warnings", []))),
            f"{r.get('duration_seconds', 0):.2f}"
        )

    table.add_section()
    table.add_row("TOTAL", str(total_docs), "", "", "", style="bold")

    console.print(table)

def main():
    parser = argparse.ArgumentParser(description="Run DFIR dataset collectors")
    parser.add_argument("--source", type=str, help="Run a specific source collector")
    parser.add_argument("--list", action="store_true", help="List available collectors")
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    config = load_config("configs/collection.yaml")

    # Map source names to (CollectorClass, config_dict)
    collector_map = {
        # Core
        "mitre_attack": (MitreAttackCollector, config["sources"].get("mitre_attack", {})),
        "sigma_rules": (SigmaRulesCollector, config["sources"].get("sigma_rules", {})),
        "atomic_red_team": (AtomicRedTeamCollector, config["sources"].get("atomic_red_team", {})),
        "cisa_advisories": (CISAAdvisoriesCollector, config["sources"].get("cisa_advisories", {})),
        "volatility3_docs": (Volatility3DocsCollector, config["sources"].get("volatility3_docs", {})),
        "mitre_atlas": (MitreAtlasCollector, config["sources"].get("mitre_atlas", {})),
        "cisa_kev": (CISAKEVCollector, config["sources"].get("cisa_kev", {})),
        # Tier 1
        "kape_files": (KapeFilesCollector, config["sources"].get("kape_files", {})),
        "hayabusa_rules": (HayabusaRulesCollector, config["sources"].get("hayabusa_rules", {})),
        "lolbas_gtfobins": (LOLBASGTFOBinsCollector, config["sources"].get("lolbas_gtfobins", {})),
        "forensic_artifacts": (ForensicArtifactsCollector, config["sources"].get("forensic_artifacts", {})),
        # Tier 2
        "velociraptor_artifacts": (VelociraptorArtifactsCollector, config["sources"].get("velociraptor_artifacts", {})),
        "hijacklibs": (HijackLibsCollector, config["sources"].get("hijacklibs", {})),
        "loldrivers": (LOLDriversCollector, config["sources"].get("loldrivers", {})),
        "ossem_data_dicts": (OSSEMDataDictsCollector, config["sources"].get("ossem_data_dicts", {})),
        "cybersec_skills": (CybersecSkillsCollector, config["sources"].get("cybersec_skills", {})),
    }

    if args.list:
        console = Console()
        console.print("\n[bold]Available collectors:[/bold]")
        for name in collector_map:
            console.print(f"  • {name}")
        console.print(f"\n[dim]Total: {len(collector_map)} collectors[/dim]")
        return

    if args.source:
        if args.source not in collector_map:
            print(f"Unknown source: {args.source}")
            print(f"Available: {', '.join(collector_map.keys())}")
            return
        to_run = [args.source]
    else:
        to_run = list(collector_map.keys())

    results = []
    for source in to_run:
        cls, src_config = collector_map[source]
        print(f"\n{'='*60}")
        print(f"  Running: {source}")
        print(f"{'='*60}")

        try:
            collector = cls(src_config)
            collector.collect()
            manifest_entry = collector.manifest()
            results.append(manifest_entry.model_dump(mode="json"))
        except Exception as e:
            print(f"  FATAL ERROR in {source}: {e}")
            results.append({
                "collector": source,
                "document_count": 0,
                "errors": [str(e)],
                "warnings": [],
                "duration_seconds": 0,
            })

    manifest_dir = Path(config.get("settings", {}).get("manifest_dir", "data/raw"))
    write_combined_manifest(results, manifest_dir)
    print_summary_table(results)

if __name__ == "__main__":
    main()
