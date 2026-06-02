import pytest
from pathlib import Path
from taxonomy.validate_taxonomy import load_taxonomy

@pytest.fixture
def taxonomy():
    taxonomy_file = Path(__file__).parent.parent / "taxonomy" / "dfir_taxonomy.yaml"
    return load_taxonomy(str(taxonomy_file))

def test_taxonomy_loads(taxonomy):
    assert taxonomy is not None
    assert taxonomy.version == "1.0"

def test_all_categories_present(taxonomy):
    assert len(taxonomy.categories) == 5
    category_ids = [c.id for c in taxonomy.categories]
    expected_ids = [
        "artifact_analysis",
        "ttp_identification",
        "triage_decision",
        "detection_engineering",
        "report_generation"
    ]
    for expected in expected_ids:
        assert expected in category_ids

def test_difficulty_distribution_sums_to_one(taxonomy):
    total = sum(taxonomy.difficulty_distribution.values())
    assert abs(total - 1.0) < 0.01

def test_category_distribution_sums_to_one(taxonomy):
    total = sum(taxonomy.category_distribution.values())
    assert abs(total - 1.0) < 0.01

def test_each_category_has_minimum_examples(taxonomy):
    for cat in taxonomy.categories:
        assert len(cat.example_tasks) >= 10, f"Category {cat.id} has less than 10 examples"

def test_difficulty_balance_per_category(taxonomy):
    for cat in taxonomy.categories:
        diff_counts = {"junior": 0, "mid": 0, "senior": 0}
        for task in cat.example_tasks:
            diff_counts[task.difficulty] += 1
            
        total = len(cat.example_tasks)
        for level, target in taxonomy.difficulty_distribution.items():
            actual = diff_counts[level] / total
            # The test just ensures it's not wildly off, our data is exactly matching or close
            assert abs(actual - target) <= 0.2, f"Category {cat.id} difficulty {level} ratio {actual} is far from target {target}"
