from typing import ClassVar

from meraki import DashboardAPI


def _normalize_mac(mac_address: str) -> str:
    """Normalize MAC address for consistent dictionary keys."""
    return mac_address.strip().lower()


class SwitchInventorySingleton:
    """
    Process-wide singleton holding switch inventory keyed by organization ID,
    then by normalized MAC. Preserves inventory_by_mac mappings across calls.
    """

    _instance: ClassVar["SwitchInventorySingleton | None"] = None
    inventory_by_mac: dict[str, dict[str, dict]]

    def __new__(cls) -> "SwitchInventorySingleton":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.inventory_by_mac = {}
        return cls._instance

    def get_switch_inventory_by_mac(
        self, dashboard: DashboardAPI, organization_id: str
    ) -> dict[str, dict]:
        """
        Download switch inventory and return devices keyed by MAC address.

        The result for each organization_id is cached for the lifetime of the process;
        subsequent calls with the same organization_id return the cached mapping.

        :param dashboard: Authenticated Dashboard API session.
        :param organization_id: Meraki organization ID.
        :return: Dictionary of inventory devices keyed by normalized MAC.
        """
        if organization_id and organization_id in self.inventory_by_mac:
            return self.inventory_by_mac[organization_id]

        print("Downloading switch inventory from the Meraki Dashboard...")
        inventory = dashboard.organizations.getOrganizationInventoryDevices(
            organization_id, productTypes=["switch"]
        )

        org_inventory_by_mac: dict[str, dict] = {}
        for device in inventory:
            mac_address = device.get("mac")
            if not mac_address:
                continue
            org_inventory_by_mac[_normalize_mac(mac_address)] = device

        if organization_id:
            self.inventory_by_mac[organization_id] = org_inventory_by_mac

        return org_inventory_by_mac


def get_switch_inventory_by_mac(
    dashboard: DashboardAPI, organization_id: str
) -> dict[str, dict]:
    """Return cached or fresh switch inventory for the organization, keyed by MAC."""
    return SwitchInventorySingleton().get_switch_inventory_by_mac(
        dashboard, organization_id
    )
