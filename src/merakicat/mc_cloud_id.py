import os
from datetime import datetime

from mc_constants import DEFAULT_FILES_FOLDER
from mc_prechecks import get_unified_os
from mc_register import (
    get_base_ethernet_macs,
    get_existing_registration_serials,
    register_stack_for_cloud_ids,
)
from netmiko import ConnectHandler
from netmiko.exceptions import ConnectionException, NetmikoTimeoutException
from paramiko.ssh_exception import AuthenticationException

try:
    from mc_user_info import DEBUG, DEBUG_REGISTER
except ImportError:
    DEBUG = DEBUG_REGISTER = False


def log_filename_suffix() -> str:
    """Return a timestamp suffix in YYYY-MM-DD-HHMMSS format."""
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")


def write_cloud_ids_log(contents: str, cloud_ids: list[str] | None = None) -> str:
    """Write get-cloud-ids output to DEFAULT_FILES_FOLDER and return file path."""
    output_dir = os.path.join(os.getcwd(), DEFAULT_FILES_FOLDER)
    os.makedirs(output_dir, exist_ok=True)
    log_file = os.path.join(output_dir, f"get-cloud-ids-{log_filename_suffix()}.log")
    if cloud_ids is None:
        cloud_ids = []
    with open(log_file, "w", encoding="utf-8") as fh:
        fh.write(contents)
        fh.write("\n")
        fh.write(
            "==========Cloud IDs one per line for pasting into the Meraki Dashboard excluding those already claimed==========\n"
        )
        if len(cloud_ids) == 0:
            fh.write("(none)\n")
        else:
            fh.write("\n".join(cloud_ids) + "\n")
    return log_file


def format_get_cloud_id_msg(host_label: str, msg: str, bot: bool = False) -> tuple[str, str]:
    """Format a single-host cloud-ID message for bot HTML or CLI log output."""
    log_line = f"{host_label:<15} {msg}\n"
    if bot:
        response_piece = "<h3>" + host_label + "</h3><p>" + msg + "</p>"
    else:
        response_piece = log_line
    return response_piece, log_line


def extract_cloud_ids_for_dashboard_paste(
    cloud_ids_with_claimed: list[tuple[dict[str, list[str]], bool]],
) -> list[str]:
    """
    Build the Cloud ID paste list for the Meraki Dashboard.

    Entries with already_claimed True are omitted.
    """
    cloud_ids: list[str] = []
    seen: set[str] = set()
    for cloud_ids_by_host, already_claimed in cloud_ids_with_claimed:
        if already_claimed:
            continue
        for ids_for_host in cloud_ids_by_host.values():
            for cloud_id in ids_for_host:
                if cloud_id not in seen:
                    seen.add(cloud_id)
                    cloud_ids.append(cloud_id)
    return cloud_ids


def format_cloud_id_lookup_msg(
    host: str,
    cloud_ids_by_host: dict[str, list[str]],
    already_claimed: bool,
    timing_short: str = "",
    bot: bool = False,
) -> tuple[str, str]:
    """Build host output/log lines from Cloud IDs and already_claimed state."""
    cloud_ids_for_host = cloud_ids_by_host.get(host, [])
    if len(cloud_ids_for_host) > 0:
        already_claimed_msg = " (already claimed) " if already_claimed else ""
        msg = ", ".join(cloud_ids_for_host) + already_claimed_msg + timing_short
    else:
        msg = "No Cloud ID returned" + timing_short
    return format_get_cloud_id_msg(host, msg, bot=bot)


def get_cloud_ids_for_host(
    host: str,
    ios_username: str,
    ios_password: str,
    ios_port: int,
    ios_secret: str,
    inventory_by_mac: dict[str, dict],
) -> tuple[dict[str, list[str]], bool]:
    """Return host-keyed Cloud IDs and already_claimed state.

    Attempts get_existing_registration_serials() first. When no IDs are found,
    performs temporary stack registration to obtain Cloud IDs.

    Parameters:
        host: Switch hostname or IP address.
        ios_username: Username for SSH.
        ios_password: Password for SSH.
        ios_port: Port number for SSH.
        ios_secret: IOSXE enable secret.
        inventory_by_mac: Map from normalized MAC to Dashboard device dict.

    Returns:
        tuple[dict[str, list[str]], bool]: host-keyed Cloud IDs and
            already_claimed flag.
    """
    debug = DEBUG or DEBUG_REGISTER
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

        base_ethernet_macs, qty_switches, _ = get_base_ethernet_macs(net_connect)

        registered_serials, already_claimed = get_existing_registration_serials(
            net_connect,
            inventory_by_mac,
            base_ethernet_macs,
            debug,
        )
        if len(registered_serials) > 0:
            return {host: registered_serials}, already_claimed

        unified_os = get_unified_os(net_connect)
        registered_serials, _, reg_issues = register_stack_for_cloud_ids(net_connect, unified_os, qty_switches, debug)

        if len(reg_issues) != 0 or len(registered_serials) == 0:
            return {host: []}, False
        return {host: registered_serials}, False
    except (AuthenticationException, NetmikoTimeoutException, ConnectionException):
        raise
    except Exception:  # pylint: disable=broad-exception-caught
        return {host: []}, False
    finally:
        net_connect.disconnect()
