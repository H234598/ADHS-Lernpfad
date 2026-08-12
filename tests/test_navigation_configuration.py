"""Regression contract for the collapsible learning navigation."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_learning_categories_use_native_collapsible_navigation() -> None:
    """Keep learning categories collapsed unless their route is active."""

    config = yaml.load(
        (ROOT / "mkdocs.yml").read_text(encoding="utf-8"),
        # safe_load rejects MkDocs' !!python/name Superfences tag. BaseLoader
        # returns strings and containers without constructing Python objects.
        Loader=yaml.BaseLoader,  # noqa: S506
    )
    features = set(config["theme"]["features"])

    assert "navigation.sections" not in features
    assert "navigation.expand" not in features
