"""Translations: every language file has exactly the keys of strings.json and keeps the placeholders."""

import json
import re
from pathlib import Path

import pytest

BASE = Path(__file__).parent.parent / "custom_components" / "snapmaker_u1_card"
LANGS = sorted(p.stem for p in (BASE / "translations").glob("*.json"))


def _flat(d, prefix=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(_flat(v, f"{prefix}{k}."))
        else:
            out[f"{prefix}{k}"] = v
    return out


def test_languages_present():
    assert {"de", "en", "es", "fr", "it", "nl", "pt", "tr"} <= set(LANGS)


@pytest.mark.parametrize("lang", LANGS)
def test_same_keys_and_placeholders(lang):
    ref = _flat(json.loads((BASE / "strings.json").read_text()))
    tr = _flat(json.loads((BASE / "translations" / f"{lang}.json").read_text()))
    assert set(tr) == set(ref), set(tr) ^ set(ref)
    ph = re.compile(r"\{\w+\}")
    for key, text in ref.items():
        assert sorted(ph.findall(tr[key])) == sorted(ph.findall(text)), (lang, key)
        # hassfest: no HTML in strings
        assert not re.search(r"<[a-zA-Z/]", tr[key]), (lang, key)
