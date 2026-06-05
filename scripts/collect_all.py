import argparse
import json
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from collectors.mitre_attack import MitreAttackCollector
from collectors.sigma_rules import SigmaRulesCollector
from collectors.atomic_red_team import AtomicRedTeamCollector
from collectors.cisa_advisories import CISAAdvisoryCollector
from collectors.cisa_kev import CISAKEVCollector

def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def write_combined_manifest(results: list[dict], manifest_dir: Path):
    manifest_dir.mkdir(parents=True, exist_ok=True)
    with open(manifest_dir / "collection_manifest.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

def print_summary_table(results: list[dict]):
    console = Console()
    table = Table(title="Collection Summary")
    table.add_column("Collector", justify="left", style="cyan", no_wrap=True)
    table.add_column("Documents", justify="right", style="magenta")
    table.add_column("Errors", justify="right", style="red")
    table.add_column("Warnings", justify="right", style="yellow")
    table.add_column("Duration (s)", justify="right", style="green")

    for r in results:
        table.add_row(
            r.get("collector", "Unknown"),
            str(r.get("document_count", 0)),
            str(len(r.get("errors", []))),
            str(len(r.get("warnings", []))),
            f"{r.get('duration_seconds', 0):.2f}"
        )

    console.print(table)

def main():
    parser = argparse.ArgumentParser(description="Run DFIR dataset collectors")
    parser.add_argument("--source", type=str, help="Run a specific source collector")
    parser.add_argument("--dry-run", action="store_true", help="Validate config without collecting")
    args = parser.parse_args()

    config = load_config("configs/collection.yaml")
    
    collector_map = {
        "mitre_attack": (MitreAttackCollector, config["sources"].get("mitre_attack", {})),
        "sigma_rules": (SigmaRulesCollector, config["sources"].get("sigma_rules", {})),
        "atomic_red_team": (AtomicRedTeamCollector, config["sources"].get("atomic_red_team", {})),
        "cisa_advisories": (CISAAdvisoryCollector, config["sources"].get("cisa_advisories", {})),
        "cisa_kev": (CISAKEVCollector, config["sources"].get("cisa_kev", {})),
    }

    if args.source:
        if args.source not in collector_map:
            print(f"Unknown source: {args.source}")
            return
        to_run = [args.source]
    else:
        to_run = list(collector_map.keys())

    if args.dry_run:
        print("Dry run: Config validation successful.")
        print(f"Would run collectors: {to_run}")
        return

    results = []
    for source in to_run:
        cls, src_config = collector_map[source]
        print(f"\n--- Running {source} ---")
        collector = cls(src_config)
        output_dir = Path(src_config.get("output_dir", f"data/raw/{source}"))
        
        collector.collect(output_dir)
        report = collector.validate(output_dir)
        
        manifest_entry = collector.manifest()
        manifest_entry.update(report)
        results.append(manifest_entry)

    write_combined_manifest(results, Path(config.get("settings", {}).get("manifest_dir", "data/raw")))
    print_summary_table(results)

if __name__ == "__main__":
    main()
