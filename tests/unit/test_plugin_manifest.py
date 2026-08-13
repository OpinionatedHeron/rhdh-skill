"""The skills CLI marketplace manifest is a projection of the catalog, not a second inventory."""

import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = PROJECT_ROOT / "scripts" / "generate_plugin_manifest.py"


def load_generator():
    """Import the generator by path; it is a repo script, not an installed module."""
    spec = importlib.util.spec_from_file_location("generate_plugin_manifest", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def check_exit_code() -> int:
    """Run `--check` in-process and return the code it exits with."""
    generator = load_generator()
    with pytest.raises(SystemExit) as exit_info:
        generator.main(["--check"])
    return exit_info.value.code


def test_the_plugin_manifest_matches_the_catalog():
    """A stale marketplace.json fails the suite."""
    assert check_exit_code() == 0, (
        "`.claude-plugin/marketplace.json` has drifted from the catalog. "
        "Regenerate it:\n"
        "  uv run python scripts/generate_plugin_manifest.py --write"
    )


def test_the_generator_can_read_its_inputs():
    """Exit 2 means the generator broke; do not conflate that with a passing check."""
    assert check_exit_code() != 2, (
        "generate_plugin_manifest.py could not read its inputs. Check that "
        f"{GENERATOR} still resolves CATALOG_PATH."
    )


def test_every_catalog_skill_is_listed_under_its_category_plugin():
    """One marketplace plugin per category; every catalog skill path appears once."""
    generator = load_generator()
    catalog = generator.json.loads(generator.CATALOG_PATH.read_text(encoding="utf-8"))
    manifest = generator.build_manifest(catalog)

    plugins = {plugin["name"]: plugin for plugin in manifest["plugins"]}
    assert list(plugins) == [generator.plugin_name(category) for category in catalog["categories"]]

    expected_paths = {
        f"./skills/{entry['category']}/{entry['name']}" for entry in catalog["skills"]
    }
    listed_paths = {path for plugin in manifest["plugins"] for path in plugin["skills"]}
    assert listed_paths == expected_paths
