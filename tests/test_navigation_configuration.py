"""Regression contract for the collapsible learning navigation."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_learning_categories_use_native_collapsible_navigation() -> None:
    """Keep learning categories collapsed unless their route is active."""

    config = yaml.load(
        (ROOT / "mkdocs.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    features = set(config["theme"]["features"])

    assert "navigation.sections" not in features
    assert "navigation.expand" not in features
