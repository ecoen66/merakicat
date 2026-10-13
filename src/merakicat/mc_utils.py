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


def parse_ios_version(show_version_output: str) -> list[str]:
    """Extract SW Version values from the switch table in show version output.

    Parses the trailing table of the form:

        Switch Ports Model              SW Version        SW Image              Mode
        ------ ----- -----              ----------        ----------            ----
        *    1 28    C9200L-24PXG-4X    17.18.04          CAT9K_LITE_IOSXE      INSTALL

    Parameters:
        show_version_output (str): Raw output from 'show version'.

    Returns:
        list[str]: SW Version strings in table order (one per stack member).
    """
    versions: list[str] = []
    in_table = False
    for raw_line in show_version_output.splitlines():
        line = raw_line.rstrip()
        if re.search(r"Switch\s+Ports\s+Model\s+SW Version", line, re.IGNORECASE):
            in_table = True
            continue
        if not in_table:
            continue
        stripped = line.strip()
        if not stripped:
            if versions:
                break
            continue
        if set(stripped) <= {"-", " "}:
            continue
        match = re.match(
            r"^\*?\s*\d+\s+\d+\s+\S+\s+(\d+(?:\.\d+)+)\s+\S+",
            stripped,
        )
        if match:
            versions.append(match.group(1))
            continue
        if versions:
            break
    return versions


def version_tuple(version: str) -> tuple[int, ...]:
    """Convert a dotted IOS version string into a comparable integer tuple.

    Parameters:
        version (str): IOS version such as '17.18.04'.

    Returns:
        tuple[int, ...]: Numeric components for comparison.
    """
    parts = [int(x) for x in re.findall(r"\d+", version)]
    return tuple(parts)


def check_minimum_ios_version(model: str, current_version: str) -> MinIosCheckResult:
    """Evaluate whether model/version satisfies the minimum required IOS.

    Parameters:
        model (str): Switch model identifier.
        current_version (str): Running IOS version on the switch.

    Returns:
        MinIosCheckResult: Evaluation result including required version and status.
    """
    compat_entry = mc_min_ios_version.get(model)
    required_version = ""
    if isinstance(compat_entry, dict):
        required_version = str(compat_entry.get("version", ""))
    elif isinstance(compat_entry, str):
        required_version = compat_entry
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

    meets = version_tuple(current_version) >= version_tuple(required_version)
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
        current_ios_versions = parse_ios_version(show_version_output)
        if not current_ios_versions:
            return check_minimum_ios_version(switch_model, "")
        lowest_version = min(current_ios_versions, key=version_tuple)
        result = check_minimum_ios_version(switch_model, lowest_version)
        return MinIosCheckResult(
            model=result.model,
            current_version=", ".join(current_ios_versions),
            required_version=result.required_version,
            meets_minimum=result.meets_minimum,
            reason=result.reason,
        )
    finally:
        net_connect.disconnect()
