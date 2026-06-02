from collections import defaultdict
from pathlib import Path
from rich.console import Console
from rich.table import Table
# Local import assuming run from project root or taxonomy dir
try:
    from validate_taxonomy import load_taxonomy
except ImportError:
    from taxonomy.validate_taxonomy import load_taxonomy

console = Console()

# Minimal hardcoded MITRE tactics for this standalone script to avoid heavy dependencies
# In a full setup, this would query STIX/mitreattack-python
TACTICS = {
    "TA0043": "Reconnaissance",
    "TA0042": "Resource Development",
    "TA0001": "Initial Access",
    "TA0002": "Execution",
    "TA0003": "Persistence",
    "TA0004": "Privilege Escalation",
    "TA0005": "Defense Evasion",
    "TA0006": "Credential Access",
    "TA0007": "Discovery",
    "TA0008": "Lateral Movement",
    "TA0009": "Collection",
    "TA0011": "Command and Control",
    "TA0010": "Exfiltration",
    "TA0040": "Impact"
}

# Mapping of some common techniques to tactics (for the example tasks)
# A real implementation would parse the STIX JSON
TECHNIQUE_TACTIC_MAP = {
    "T1036.005": ["Defense Evasion"],
    "T1021.001": ["Lateral Movement"],
    "T1059": ["Execution"],
    "T1014": ["Defense Evasion"],
    "T1055.001": ["Defense Evasion", "Privilege Escalation"],
    "T1106": ["Execution"],
    "T1547.001": ["Persistence", "Privilege Escalation"],
    "T1078": ["Defense Evasion", "Persistence", "Privilege Escalation", "Initial Access"],
    "T1055.012": ["Defense Evasion", "Privilege Escalation"],
    "T1059.001": ["Execution"],
    "T1053.005": ["Execution", "Persistence", "Privilege Escalation"],
    "T1021.002": ["Lateral Movement"],
    "T1070.001": ["Defense Evasion"],
    "T1047": ["Execution"],
    "T1074.001": ["Collection"]
}

def main():
    try:
        taxonomy_file = Path(__file__).parent / "dfir_taxonomy.yaml"
        if not taxonomy_file.exists():
            # Try running from project root
            taxonomy_file = Path("taxonomy/dfir_taxonomy.yaml")
    except NameError:
        taxonomy_file = Path("taxonomy/dfir_taxonomy.yaml")

    taxonomy = load_taxonomy(str(taxonomy_file))
    if not taxonomy:
        return

    # Count techniques per tactic
    tactic_counts = defaultdict(int)
    techniques_found = set()

    for cat in taxonomy.categories:
        for task in cat.example_tasks:
            for tech in task.mitre_techniques:
                techniques_found.add(tech)
                # Map to tactic
                tactics = TECHNIQUE_TACTIC_MAP.get(tech, [])
                if not tactics:
                    # Generic mapping if not in our hardcoded dictionary (e.g. wildcard)
                    if tech.startswith("T1055"):
                        tactics = ["Defense Evasion", "Privilege Escalation"]
                    else:
                        tactics = ["Unknown"]
                for t in tactics:
                    tactic_counts[t] += 1

    # Display results
    console.print("\n[bold]MITRE ATT&CK Tactic Coverage Heatmap[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Tactic")
    table.add_column("Coverage (Count)")
    table.add_column("Status")

    for tactic_id, tactic_name in TACTICS.items():
        count = tactic_counts.get(tactic_name, 0)
        
        # Simple text-based bar chart
        bar = "█" * min(count, 10) + "░" * max(0, 10 - count)
        
        status = "[green]Covered[/green]" if count > 0 else "[red]Missing[/red]"
        table.add_row(tactic_name, f"{bar} ({count})", status)
        
    console.print(table)
    
    missing = sum(1 for t in TACTICS.values() if tactic_counts.get(t, 0) == 0)
    if missing > 0:
        console.print(f"\n[yellow]Warning: {missing} tactics have no coverage in the example tasks.[/yellow]")
        console.print("This is expected for a small sample of 50 tasks, but flag if a core tactic is missing.")
    else:
        console.print("\n[green]Excellent: All tactics have some coverage.[/green]")

if __name__ == "__main__":
    main()
