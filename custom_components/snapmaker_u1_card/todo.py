"""2.4: HA to-do lists – due maintenance and a filament shopping list.

Both are options and off by default; without them no entity exists and nothing
is computed. The lists are built from data the integration has anyway (the
maintenance status of every update, the Spoolman spool list of its regular
refresh), so they cost no extra request to the printer or Spoolman.

Maintenance: every due item; ticking it off marks it done (same as in the
card). The firmware's tool changer counter is shown but cannot be ticked off
here – it is reset on the printer.

Shopping list: active spools below the low-stock threshold. Ticking off or
removing an item is remembered until the spool is no longer low (refilled,
archived, deleted). With the option ``shopping_target`` the items go to an
existing list instead (see SpoolMixin._shopping_check) and no own entity is
created.
"""

from __future__ import annotations

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import U1ConfigEntry
from .const import (
    CONF_SHOPPING_TARGET,
    CONF_SPOOLMAN_URL,
    CONF_TODO_MAINT,
    CONF_TODO_SHOPPING,
)
from .i18n import tr
from .sensor import U1Entity
from .stats import MAINTENANCE_ITEMS, maintenance_label


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the lists that are switched on (option change reloads the entry)."""
    coordinator = entry.runtime_data
    opts = coordinator.options
    entities: list[TodoListEntity] = []
    if opts.get(CONF_TODO_MAINT):
        entities.append(MaintenanceTodo(coordinator))
    if opts.get(CONF_TODO_SHOPPING) and opts.get(CONF_SPOOLMAN_URL) and not opts.get(CONF_SHOPPING_TARGET):
        entities.append(ShoppingTodo(coordinator))
    async_add_entities(entities)


class MaintenanceTodo(U1Entity, TodoListEntity):
    """Due maintenance items."""

    _attr_translation_key = "maintenance_todo"
    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "maintenance_todo")

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None  # counts in print hours: also while the printer is off

    @property
    def todo_items(self) -> list[TodoItem]:
        data = self.coordinator.data
        de = self.hass.config.language.lower().startswith("de")
        items = []
        for m in (data.maintenance if data else None) or []:
            if not m.get("due"):
                continue
            label = maintenance_label(m["key"], de) if m["key"] in MAINTENANCE_ITEMS else (
                "Werkzeugwechsler (am Drucker zurücksetzen)" if de else "Tool changer (reset on the printer)")
            items.append(TodoItem(summary=label, uid=m["key"], status=TodoItemStatus.NEEDS_ACTION,
                                  description=self._detail(m, de)))
        return items

    @staticmethod
    def _detail(m: dict, de: bool) -> str | None:
        """How far past the interval it is, in the unit that made it due."""
        if m.get("by") == "months" and m.get("interval_m"):
            late = -float(m.get("remaining_d") or 0)
            every = f"{'alle' if de else 'every'} {m['interval_m']} {'Monate' if de else 'months'}"
            return f"{every} · {round(late)} {'Tage überfällig' if de else 'days overdue'}" if late >= 1 else every
        if m.get("interval_h"):
            return f"{m.get('used_h')} / {m['interval_h']} h"
        if m.get("interval"):
            return f"{m.get('used')} / {m['interval']}"
        return None

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Ticked off = maintenance done now."""
        if item.status != TodoItemStatus.COMPLETED:
            return
        if item.uid not in MAINTENANCE_ITEMS:
            raise HomeAssistantError(tr(self.hass, "Der Werkzeugwechsel-Zähler wird am Drucker zurückgesetzt.",
                                        "The tool changer counter is reset on the printer."))
        self.coordinator.mark_maintenance(item.uid)


class ShoppingTodo(U1Entity, TodoListEntity):
    """Spools that are running low."""

    _attr_translation_key = "shopping_todo"
    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM | TodoListEntityFeature.DELETE_TODO_ITEM

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "shopping_todo")

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None and self.coordinator.spools.online

    @property
    def todo_items(self) -> list[TodoItem]:
        state = self.coordinator.shopping["state"]
        items = []
        for s in self.coordinator.shopping_spools():
            mark = state.get(str(s["id"]))
            if mark == "hidden":
                continue
            rest = s.get("remaining_weight")
            detail = " · ".join(p for p in (f"#{s['id']}", f"{round(rest)} g" if rest is not None else None,
                                            s.get("location")) if p)
            items.append(TodoItem(summary=self.coordinator.shopping_text(s), uid=f"spool-{s['id']}", description=detail,
                                  status=TodoItemStatus.COMPLETED if mark == "done" else TodoItemStatus.NEEDS_ACTION))
        return items

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Ticked off = bought (stays ticked until the spool is no longer low)."""
        self.coordinator.set_shopping_state(_spool_id(item.uid),
                                            "done" if item.status == TodoItemStatus.COMPLETED else None)

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Removed = not wanted; comes back only when the spool was refilled and runs low again."""
        for uid in uids:
            self.coordinator.set_shopping_state(_spool_id(uid), "hidden")


def _spool_id(uid: str | None) -> int:
    try:
        return int(str(uid).removeprefix("spool-"))
    except ValueError as err:
        raise HomeAssistantError(f"Unknown item {uid}") from err
