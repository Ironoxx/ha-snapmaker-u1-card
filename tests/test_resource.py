"""Zweiter Ladeweg: Karte als Dashboard-Ressource unter /local."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.components.lovelace import LovelaceData  # noqa: E402
from homeassistant.components.lovelace.const import LOVELACE_DATA  # noqa: E402
from homeassistant.components.lovelace.resources import ResourceStorageCollection  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402

from tests.test_init import DOMAIN, _setup, mock_client  # noqa: E402,F401


@pytest.fixture(autouse=True)
def auto_enable(enable_custom_integrations, hass, tmp_path):
    hass.config.components.add("frontend")
    hass.config.config_dir = str(tmp_path)
    yield


@pytest.fixture
def storage_resources(hass: HomeAssistant):
    ll_config = MagicMock(async_load=AsyncMock(return_value={}))
    coll = ResourceStorageCollection(hass, ll_config)
    hass.data[LOVELACE_DATA] = LovelaceData(
        resource_mode="storage", dashboards={}, resources=coll, yaml_dashboards={}
    )
    return coll


def _ours(coll):
    return [i for i in coll.async_items() if i["url"].startswith(f"/local/{DOMAIN}/")]


async def test_resource_created_and_file_copied(hass: HomeAssistant, mock_client) -> None:
    from custom_components.snapmaker_u1_card.const import VERSION

    await _setup(hass)
    # Echtes Lovelace (Abhaengigkeit der Integration), Speicher-Modus
    coll = hass.data[LOVELACE_DATA].resources
    assert hass.data[LOVELACE_DATA].resource_mode == "storage"
    items = _ours(coll)
    assert len(items) == 1
    assert items[0]["url"] == f"/local/{DOMAIN}/snapmaker-u1-card.js?v={VERSION}"
    assert items[0]["type"] == "module"
    copied = Path(hass.config.path("www", DOMAIN, "snapmaker-u1-card.js"))
    src = Path(__file__).parents[1] / "custom_components" / DOMAIN / "frontend" / "snapmaker-u1-card.js"
    assert copied.read_bytes() == src.read_bytes()


async def test_resource_updated_and_deduplicated(hass: HomeAssistant, storage_resources) -> None:
    from custom_components.snapmaker_u1_card import resource
    from custom_components.snapmaker_u1_card.const import VERSION

    await storage_resources.async_load()
    storage_resources.loaded = True
    other = await storage_resources.async_create_item({"res_type": "module", "url": "/hacsfiles/x/x.js"})
    await storage_resources.async_create_item({"res_type": "module", "url": f"/local/{DOMAIN}/snapmaker-u1-card.js?v=1.0.0"})
    await storage_resources.async_create_item({"res_type": "js", "url": f"/local/{DOMAIN}/snapmaker-u1-card.js?v=0.9"})
    await resource.async_install(hass)
    items = _ours(storage_resources)
    assert [(i["url"], i["type"]) for i in items] == [(f"/local/{DOMAIN}/snapmaker-u1-card.js?v={VERSION}", "module")]
    assert other in storage_resources.async_items(), "fremde Ressourcen bleiben"
    # zweiter Lauf aendert nichts
    await resource.async_install(hass)
    assert len(_ours(storage_resources)) == 1


async def test_yaml_mode_untouched(hass: HomeAssistant) -> None:
    from custom_components.snapmaker_u1_card import resource

    yaml_coll = MagicMock()
    hass.data[LOVELACE_DATA] = LovelaceData(
        resource_mode="yaml", dashboards={}, resources=yaml_coll, yaml_dashboards={}
    )
    await resource.async_install(hass)
    yaml_coll.async_create_item.assert_not_called()
    # Datei liegt trotzdem bereit (fuer eine eigene YAML-Ressource)
    assert Path(hass.config.path("www", DOMAIN, "snapmaker-u1-card.js")).exists()


async def test_removed_with_last_entry(hass: HomeAssistant, mock_client) -> None:
    entry = await _setup(hass)
    coll = hass.data[LOVELACE_DATA].resources
    assert _ours(coll)
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert not _ours(coll)
    assert not Path(hass.config.path("www", DOMAIN)).exists()
