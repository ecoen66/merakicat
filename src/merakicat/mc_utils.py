# Common utility functions / classes
import re
from dataclasses import dataclass

from mc_min_ios_version import mc_min_ios_version
from netmiko import BaseConnection, ConnectHandler
from ntc_templates.parse import parse_output


@dataclass(frozen=True)
class MinIosCheckResult:
    model: str
    current_version: str
    required_version: str
    meets_minimum: bool | None
    reason: str


def normalize_mac(mac_address: str) -> str:
    """Convert dotted Cisco MAC format into colon-separated octets."""
    compact_mac = mac_address.strip().lower().replace(".", "")
    return ":".join(
        compact_mac[index : index + 2] for index in range(0, len(compact_mac), 2)
    )


def get_switch_model(net_connect: BaseConnection) -> str:
    """Get switch model from parsed 'show inventory' output."""
    show_inventory = net_connect.send_command("show inventory")
    show_inventory_parsed = parse_output(
        platform="cisco_ios",
        command="show inventory",
        data=show_inventory,
    )
    if not show_inventory_parsed:
        return ""

    for row in show_inventory_parsed:
        if not isinstance(row, dict):
            continue
        for key in ("model", "pid", "platform", "chassis", "chassis_type"):
            value = row.get(key)
            if value:
                return str(value)

    return ""


def parse_ios_version(show_version_output: str) -> str:
    """Extract IOS version from show version output using parse_output first."""
    parsed = parse_output(
        platform="cisco_ios",
        command="show version",
        data=show_version_output,
    )
    if not parsed:
        return ""

    for row in parsed:
        if not isinstance(row, dict):
            continue
        for key in ("version", "os_version", "software_version"):
            value = row.get(key)
            if value:
                return str(value)

    return ""


def _version_tuple(version: str) -> tuple[int, ...]:
    parts = [int(x) for x in re.findall(r"\d+", version)]
    return tuple(parts)


def check_minimum_ios_version(model: str, current_version: str) -> MinIosCheckResult:
    """Evaluate whether model/version satisfies the minimum required IOS."""
    required_version = mc_min_ios_version.get(model, "")
    if not model:
        return MinIosCheckResult(
            model="",
            current_version=current_version,
            required_version="",
            meets_minimum=None,
            reason="unknown_model",
        )
    if not required_version:
        return MinIosCheckResult(
            model=model,
            current_version=current_version,
            required_version="",
            meets_minimum=None,
            reason="unsupported_model",
        )
    if not current_version:
        return MinIosCheckResult(
            model=model,
            current_version="",
            required_version=required_version,
            meets_minimum=None,
            reason="unknown_version",
        )

    meets = _version_tuple(current_version) >= _version_tuple(required_version)
    return MinIosCheckResult(
        model=model,
        current_version=current_version,
        required_version=required_version,
        meets_minimum=meets,
        reason="met" if meets else "not_met",
    )


def check_host_minimum_ios(
    host: str,
    ios_username: str,
    ios_password: str,
    ios_port: int,
    ios_secret: str,
) -> MinIosCheckResult:
    """Connect to a host and evaluate model + minimum IOS support."""
    session_info = {
        "device_type": "cisco_xe",
        "host": host,
        "username": ios_username,
        "password": ios_password,
        "port": ios_port,
        "secret": ios_secret,
    }
    net_connect = ConnectHandler(**session_info)
    try:
        net_connect.enable()
        switch_model = get_switch_model(net_connect)
        support_probe = check_minimum_ios_version(switch_model, "0.0.0")
        if support_probe.reason in {"unsupported_model", "unknown_model"}:
            return support_probe
        show_version_output = str(net_connect.send_command("show version"))
        current_ios_version = parse_ios_version(show_version_output)
        return check_minimum_ios_version(switch_model, current_ios_version)
    finally:
        net_connect.disconnect()
