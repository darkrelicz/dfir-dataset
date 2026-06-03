import re
import sys
import yaml

from pathlib import Path
from pydantic import BaseModel, ValidationError, field_validator
from rich.console import Console
from typing import Literal, Dict, List, Optional


console = Console()

class ExampleTask(BaseModel):
    id: str
    instruction: str
    difficulty: Literal["junior", "mid", "senior"]
    mitre_techniques: List[str] = []
    tools: List[str] = []
    reasoning_focus: str
    sub_category: Optional[str] = None

    @field_validator("mitre_techniques")
    @classmethod
    def validate_mitre_id(cls, techniques: List[str]) -> List[str]:
        for technique in techniques:
            if not re.match(r"^T\d{4}(\.\d{3})?$", technique):
                raise ValueError(f"Invalid MITRE ATT&CK technique ID format: {technique}")
        return techniques

class SubCategory(BaseModel):
    id: str
    name: str
    description: str
    primary_sources: List[str] = []

class Category(BaseModel):
    id: str
    name: str
    description: str
    shepherd_alignment: List[str]
    priority: Literal["critical", "high", "medium"]
    sub_categories: List[SubCategory] = []
    example_tasks: List[ExampleTask]

class Taxonomy(BaseModel):
    version: str
    description: str
    date_created: str
    date_updated: str
    difficulty_distribution: Dict[str, float]
    category_distribution: Dict[str, float]
    categories: List[Category]

def load_taxonomy(file_path: str) -> Optional[Taxonomy]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return Taxonomy(**data)
    except FileNotFoundError:
        console.print(f"[red]Error: Could not find {file_path}[/red]")
        sys.exit(1)
    except yaml.YAMLError as e:
        console.print(f"[red]Error parsing YAML in {file_path}: {e}[/red]")
        sys.exit(1)
    except ValidationError as e:
        console.print(f"[red]Schema validation error in {file_path}:[/red]")
        console.print(e)
        sys.exit(1)

def run_checks(taxonomy: Taxonomy) -> bool:
    passed = True
    console.print(f"[bold]Validating Taxonomy (v{taxonomy.version})[/bold]\n")

    # 1. Distribution totals
    diff_total = sum(taxonomy.difficulty_distribution.values())
    if abs(diff_total - 1.0) > 0.01:
        console.print(f"[red]✗ Difficulty distribution sums to {diff_total:.2f} (expected 1.0)[/red]")
        passed = False
    else:
        console.print("[green]✓ Difficulty distribution sums to 1.0[/green]")

    cat_total = sum(taxonomy.category_distribution.values())
    if abs(cat_total - 1.0) > 0.01:
        console.print(f"[red]✗ Category distribution sums to {cat_total:.2f} (expected 1.0)[/red]")
        passed = False
    else:
        console.print("[green]✓ Category distribution sums to 1.0[/green]")

    # 2. Category checks
    for cat in taxonomy.categories:
        if len(cat.example_tasks) < 10:
            console.print(f"[red]✗ Category '{cat.id}' has {len(cat.example_tasks)} example tasks (minimum 10)[/red]")
            passed = False
        else:
            console.print(f"[green]✓ Category '{cat.id}' has ≥10 example tasks[/green]")
        
        # Difficulty balance per category
        diff_counts = {"junior": 0, "mid": 0, "senior": 0}
        for task in cat.example_tasks:
            diff_counts[task.difficulty] += 1
        
        total_tasks = len(cat.example_tasks)
        for level, target in taxonomy.difficulty_distribution.items():
            actual = diff_counts[level] / total_tasks
            if abs(actual - target) > 0.1:
                console.print(f"[yellow]! Warning: Category '{cat.id}' '{level}' ratio is {actual:.2f} (target {target:.2f})[/yellow]")

    return passed

def main():
    taxonomy_file = Path(__file__).parent / "dfir_taxonomy.yaml"
    taxonomy = load_taxonomy(str(taxonomy_file))
    
    if taxonomy:
        success = run_checks(taxonomy)
        if success:
            console.print("\n[bold green]Validation passed successfully![/bold green]")
        else:
            console.print("\n[bold red]Validation failed.[/bold red]")
            sys.exit(1)

if __name__ == "__main__":
    main()
