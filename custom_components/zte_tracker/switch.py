"""Switch platform for ZTE Tracker."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_REGISTER_NEW_DEVICES, DOMAIN
from .coordinator import ZteDataCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZTE tracker switches from config entry."""
    coordinator: ZteDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ZtePauseSwitch(coordinator, entry),
            ZteRegisterNewDevicesSwitch(coordinator, entry),
        ]
    )

    added_wifi_ids: set[str] = set()

    def add_wifi_entities() -> None:
        """Add newly discovered WLAN APs without duplicating entities."""
        wifi = (coordinator.data or {}).get("wifi", [])
        counts: dict[str, int] = {}
        for ap in wifi:
            ssid = ap.get("ssid", "")
            if ssid:
                counts[ssid] = counts.get(ssid, 0) + 1

        entities: list[ZteWifiSwitch] = []
        for ap in wifi:
            ap_id = ap.get("ap_id")
            ssid = ap.get("ssid", "")
            if not ap_id or not ssid or ap_id in added_wifi_ids:
                continue
            band = ap.get("band", "")
            name = ssid
            if counts.get(ssid, 0) > 1 and band:
                name = f"{ssid} {band}"
            entities.append(ZteWifiSwitch(coordinator, entry, ap_id, name))
            added_wifi_ids.add(ap_id)

        if entities:
            async_add_entities(entities)

    add_wifi_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_wifi_entities))


class ZteWifiSwitch(CoordinatorEntity, SwitchEntity):
    """Switch controlling one physical WLAN access point."""

    def __init__(
        self,
        coordinator: ZteDataCoordinator,
        entry: ConfigEntry,
        ap_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._ap_id = ap_id
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_wifi_{ap_id.lower()}"
        self._attr_icon = "mdi:wifi"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ZTE Router {coordinator.client.host}",
            manufacturer="ZTE",
            model=coordinator.client.model,
        )

    def _current_ap(self) -> dict | None:
        """Return the latest AP data from the coordinator."""
        return next(
            (
                ap
                for ap in ((self.coordinator.data or {}).get("wifi", []))
                if ap.get("ap_id") == self._ap_id
            ),
            None,
        )

    @property
    def is_on(self) -> bool | None:
        """Return the router-confirmed AP state."""
        ap = self._current_ap()
        return ap.get("enabled") if ap else None

    @property
    def available(self) -> bool:
        """Return whether the AP is present and the coordinator is online."""
        return super().available and self._current_ap() is not None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Expose non-secret WLAN metadata."""
        ap = self._current_ap()
        if not ap:
            return {}
        return {
            "ap_id": ap.get("ap_id", ""),
            "band": ap.get("band", ""),
            "radio_id": ap.get("radio_id", ""),
            "alias": ap.get("alias", ""),
        }

    async def async_turn_on(self, **kwargs) -> None:
        """Enable this WLAN AP."""
        await self.coordinator.async_set_wifi_enabled(self._ap_id, True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable this WLAN AP."""
        await self.coordinator.async_set_wifi_enabled(self._ap_id, False)


class ZtePauseSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to pause/resume the tracker."""

    def __init__(self, coordinator: ZteDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "ZTE Tracker Pause"
        self._attr_unique_id = f"{entry.entry_id}_pause_switch"
        self._attr_icon = "mdi:pause-circle"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ZTE Router {coordinator.client.host}",
            manufacturer="ZTE",
            model=coordinator.client.model,
        )

    @property
    def is_on(self) -> bool:
        """Return True if tracker is paused."""
        # Ensure coordinator is ZteDataCoordinator
        if hasattr(self.coordinator, "paused"):
            return self.coordinator.paused
        return False

    async def async_turn_on(self, **kwargs) -> None:
        """Pause the tracker."""
        if hasattr(self.coordinator, "pause_scanning"):
            self.coordinator.pause_scanning()
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Resume the tracker."""
        if hasattr(self.coordinator, "resume_scanning"):
            self.coordinator.resume_scanning()
            await self.coordinator.async_request_refresh()


class ZteRegisterNewDevicesSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to control registration of new devices."""

    def __init__(self, coordinator: ZteDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "ZTE Register New Devices"
        self._attr_unique_id = f"{entry.entry_id}_register_new_devices"
        self._attr_icon = "mdi:lan-connect"
        self._default_register = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ZTE Router {coordinator.client.host}",
            manufacturer="ZTE",
            model=coordinator.client.model,
        )

    @property
    def is_on(self) -> bool:
        """Return True if new devices will be registered."""
        if hasattr(self.coordinator, "register_new_devices"):
            return self.coordinator.register_new_devices
        return self._default_register

    async def _async_update_entry_option(self, enabled: bool) -> None:
        """Persist the register new devices option in the config entry."""
        if not self.hass or not hasattr(self.hass, "config_entries"):
            return
        current = self._entry.options.get(
            CONF_REGISTER_NEW_DEVICES, self._default_register
        )
        if current == enabled:
            return
        updated_options = dict(self._entry.options)
        updated_options[CONF_REGISTER_NEW_DEVICES] = enabled
        self.hass.config_entries.async_update_entry(
            self._entry, options=updated_options
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Enable registration of new devices."""
        self.coordinator.enable_register_new_devices()
        await self._async_update_entry_option(True)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable registration of new devices."""
        self.coordinator.disable_register_new_devices()
        await self._async_update_entry_option(False)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
