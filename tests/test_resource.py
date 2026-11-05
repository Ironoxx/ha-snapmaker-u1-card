"""The card as a dashboard resource from the integration's static path (2.1.2)."""

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
    return [i for i in coll.async_items()
            if i["url"].split("?")[0] in (f"/{DOMAIN}/card/snapmaker-u1-card.js", f"/local/{DOMAIN}/snapmaker-u1-card.js")]


async def test_resource_points_to_the_integration(hass: HomeAssistant, mock_client) -> None:
    """hacs/default review: no copy in /config/www, the resource uses the integration's static path."""
    from custom_components.snapmaker_u1_card.const import VERSION

    await _setup(hass)
    coll = hass.data[LOVELACE_DATA].resources
    assert hass.data[LOVELACE_DATA].resource_mode == "storage"
    items = _ours(coll)
    assert [(i["url"], i["type"]) for i in items] == [(f"/{DOMAIN}/card/snapmaker-u1-card.js?v={VERSION}", "module")]
    assert not Path(hass.config.path("www", DOMAIN)).exists(), "nothing written to /config/www"


async def test_old_resource_and_copy_migrated(hass: HomeAssistant, storage_resources) -> None:
    from custom_components.snapmaker_u1_card import resource
    from custom_components.snapmaker_u1_card.const import VERSION

    www = Path(hass.config.path("www"))
    (www / DOMAIN).mkdir(parents=True)
    (www / DOMAIN / "snapmaker-u1-card.js").write_text("old card")
    (www / "u1_top.png").write_text("user file")
    await storage_resources.async_load()
    storage_resources.loaded = True
    other = await storage_resources.async_create_item({"res_type": "module", "url": "/hacsfiles/x/x.js"})
    await storage_resources.async_create_item({"res_type": "module", "url": f"/local/{DOMAIN}/snapmaker-u1-card.js?v=2.1.1"})
    await storage_resources.async_create_item({"res_type": "js", "url": f"/local/{DOMAIN}/snapmaker-u1-card.js?v=0.9"})
    await resource.async_install(hass)
    items = _ours(storage_resources)
    assert [(i["url"], i["type"]) for i in items] == [(f"/{DOMAIN}/card/snapmaker-u1-card.js?v={VERSION}", "module")]
    assert other in storage_resources.async_items(), "fremde Ressourcen bleiben"
    assert not (www / DOMAIN).exists(), "own old copy removed"
    assert (www / "u1_top.png").read_text() == "user file", "nothing else touched"
    # a second run changes nothing
    await resource.async_install(hass)
    assert len(_ours(storage_resources)) == 1


async def test_legacy_folder_with_user_files_kept(hass: HomeAssistant) -> None:
    from custom_components.snapmaker_u1_card import resource

    folder = Path(hass.config.path("www", DOMAIN))
    folder.mkdir(parents=True)
    (folder / "snapmaker-u1-card.js").write_text("old card")
    (folder / "mine.png").write_text("x")
    await resource.async_install(hass)
    assert not (folder / "snapmaker-u1-card.js").exists() and (folder / "mine.png").exists()


async def test_yaml_mode_untouched(hass: HomeAssistant) -> None:
    from custom_components.snapmaker_u1_card import resource

    yaml_coll = MagicMock()
    hass.data[LOVELACE_DATA] = LovelaceData(
        resource_mode="yaml", dashboards={}, resources=yaml_coll, yaml_dashboards={}
    )
    await resource.async_install(hass)
    yaml_coll.async_create_item.assert_not_called()


async def test_removed_with_last_entry(hass: HomeAssistant, mock_client) -> None:
    entry = await _setup(hass)
    coll = hass.data[LOVELACE_DATA].resources
    assert _ours(coll)
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert not _ours(coll)
