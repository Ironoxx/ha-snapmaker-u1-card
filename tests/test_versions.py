"""Release guard: the version number is identical everywhere, translations are complete."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "snapmaker_u1_card"


def test_versions_match():
    manifest = json.loads((PKG / "manifest.json").read_text())["version"]
    const = re.search(r'VERSION = "([^"]+)"', (PKG / "const.py").read_text()).group(1)
    card = re.search(r'CARD_VERSION = "([^"]+)"', (PKG / "frontend" / "snapmaker-u1-card.js").read_text()).group(1)
    src = re.search(r'CARD_VERSION = "([^"]+)"', (ROOT / "frontend" / "src" / "const.js").read_text()).group(1)
    assert manifest == const == card == src


def test_translations_complete():
    def keys(d, prefix=""):
        out = set()
        for k, v in d.items():
            out |= keys(v, f"{prefix}{k}.") if isinstance(v, dict) else {f"{prefix}{k}"}
        return out

    strings = keys(json.loads((PKG / "strings.json").read_text()))
    for lang in ("en", "de"):
        assert keys(json.loads((PKG / "translations" / f"{lang}.json").read_text())) == strings, lang


def test_services_yaml_valid():
    """services.yaml as Home Assistant validates it on load; every service translated."""
    import pytest

    yaml = pytest.importorskip("yaml")
    service = pytest.importorskip("homeassistant.helpers.service")
    data = yaml.safe_load((PKG / "services.yaml").read_text())
    service._SERVICES_SCHEMA(data)
    strings = json.loads((PKG / "strings.json").read_text())["services"]
    assert set(data) == set(strings)
    for name, spec in data.items():
        assert set((spec or {}).get("fields") or {}) == set(strings[name].get("fields") or {}), name
