"""Regression contract for the collapsible learning navigation."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_learning_categories_use_native_collapsible_navigation() -> None:
    """Keep learning categories collapsed unless their route is active."""

    text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    # safe_load rejects MkDocs' !!python/name Superfences tag. BaseLoader
    # returns only strings and containers and never constructs Python objects.
    config = yaml.BaseLoader(text).get_single_data()
    features = set(config["theme"]["features"])

    assert "navigation.sections" not in features
    assert "navigation.expand" not in features
