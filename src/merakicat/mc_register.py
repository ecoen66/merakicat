import os
import re
import time
from dataclasses import dataclass

from netmiko import ConnectHandler
from ntc_templates.parse import parse_output
import textfsm

from mc_get_nms import GetNmList
from mc_meraki_dry_run import MERAKI_DRY_RUN
from mc_prechecks import prechecks
from mc_utils import get_switch_model, normalize_mac


try:
    from mc_user_info import DEBUG, DEBUG_REGISTER
except ImportError:
    DEBUG = DEBUG_REGISTER = False


@dataclass(frozen=True)
class MgmtCommands:
    show_mgmt: str
    connect_mgmt: str
    no_connect_mgmt: str


def get_mgmt_commands_for_model(switch_model: str) -> MgmtCommands:
    """Return platform-specific management commands."""
    if re.match(r"IE-350.-.*", switch_model):
        connect_mgmt = "service cloud-mgmt connect"
        return MgmtCommands(
            show_mgmt="show cloud-mgmt",
            connect_mgmt=connect_mgmt,
            no_connect_mgmt=f"no {connect_mgmt}",
        )

    connect_mgmt = "service meraki connect"
    return MgmtCommands(
        show_mgmt="show meraki",
        connect_mgmt=connect_mgmt,
        no_connect_mgmt=f"no {connect_mgmt}",
    )


def get_existing_registration_serials(
    net_connect,
    inventory_by_mac: dict[str, dict],
    base_ethernet_macs: list[str],
    debug: bool = False,
) -> tuple[list[str], bool]:
    """Detect whether the switch is already claimed or has a cloud ID.

    Checks Dashboard inventory by base Ethernet MAC first, then parses
    show meraki / show cloud-mgmt output on the device.

    Parameters:
        net_connect: Active netmiko connection to the switch.
        inventory_by_mac: Map from normalized MAC to Dashboard device dict.
        base_ethernet_macs: Normalized base Ethernet MACs from show switch.
        debug: When True, print CLI output for cloud-ID lookup.

    Returns:
        tuple[list[str], bool]: registered_serials and already_claimed.
    """
    matching_serials: list[str] = []
    for base_mac in base_ethernet_macs:
        device = inventory_by_mac.get(base_mac)
        if not device:
            continue
        serial = device.get("serial")
        if serial and serial not in matching_serials:
            matching_serials.append(serial)
    if len(matching_serials) > 0:
        return matching_serials, True

    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_file = os.path.join(script_dir, "show-meraki.textfsm")
    with open(template_file, encoding="utf-8") as template_file_fh:
        fsm = textfsm.TextFSM(template_file_fh)

    switch_model = get_switch_model(net_connect)
    mgmt_commands = get_mgmt_commands_for_model(switch_model)

    show_mgmt_output = net_connect.send_command_timing(mgmt_commands.show_mgmt, strip_prompt=True, strip_command=True)
    if debug:
        print(show_mgmt_output)
    show_meraki_parsed = fsm.ParseTextToDicts(show_mgmt_output)
    if show_meraki_parsed and len(show_meraki_parsed) > 0 and "cloud_id" in show_meraki_parsed[0]:
        cloud_ids = [item["cloud_id"] for item in show_meraki_parsed]
        return cloud_ids, False

    return [], False


def get_base_ethernet_macs(
    net_connect,
) -> tuple[list[str], int, list[dict]]:
    """Parse show switch output for normalized base Ethernet MACs.

    Parameters:
        net_connect: Active netmiko connection to the switch.

    Returns:
        tuple[list[str], int, list[dict]]: base_ethernet_macs, qty_switches,
            and parsed show switch rows.
    """
    show_switch = str(net_connect.send_command("show switch"))
    qty_switches = len(show_switch.split("\n")) - 8
    show_switch_parsed = parse_output(
        platform="cisco_ios",
        command="show switch",
        data=show_switch,
    )
    base_ethernet_macs: list[str] = []
    for item in show_switch_parsed:
        mac_address = item["mac_address"]
        base_ethernet_macs.append(normalize_mac(mac_address))
    return base_ethernet_macs, qty_switches, show_switch_parsed


def register_stack_for_cloud_ids(
    net_connect,
    unified_os: bool,
    qty_switches: int,
    debug: bool = False,
) -> tuple[list[str], list[dict], list[str]]:
    """Register all stack members temporarily and return Cloud IDs.

    For unified OS switches, disconnects cloud management after reading IDs.

    Parameters:
        net_connect: Active netmiko connection to the switch.
        unified_os: Whether the switch runs unified IOS XE management.
        qty_switches: Number of switches in the stack.
        debug: When True, print CLI output.

    Returns:
        tuple[list[str], list[dict], list[str]]: registered_serials,
            registered_switches, and issues (non-empty on failure).
    """
    registered_switches: list[dict] = []
    registered_serials: list[str] = []
    issues: list[str] = []

    switch_model = get_switch_model(net_connect)
    mgmt_commands = get_mgmt_commands_for_model(switch_model)

    if unified_os is False:
        r = net_connect.send_command_timing(
            "service meraki register switch all",
            strip_prompt=False,
            strip_command=False,
        )
        if debug:
            print(r)
        if not r.find("Are you sure") == -1:  # type: ignore
            r = net_connect.send_command_timing("yes", strip_prompt=False, strip_command=False)
            if debug:
                print(r)
    else:
        if MERAKI_DRY_RUN:
            print(f"[DRY-RUN] Skipped: {mgmt_commands.connect_mgmt}")
            issues.append("No registration status returned.")
            return registered_serials, registered_switches, issues
        r = net_connect.send_command_timing("conf t", strip_prompt=False, strip_command=False)
        if debug:
            print(r)
        r = net_connect.send_command_timing(mgmt_commands.connect_mgmt, strip_prompt=False, strip_command=False)
        if debug:
            print(r)
        r = net_connect.send_command_timing("exit", strip_prompt=False, strip_command=False)
        if debug:
            print(r)
        time.sleep(10)
        r = net_connect.send_command_timing(mgmt_commands.show_mgmt, strip_prompt=False, strip_command=False)
        if debug:
            print(r)

    r_more = r.split("\n")  # type: ignore
    if debug:
        print(f"r_more = {r_more}")

    regex = re.compile("^1")
    top_matches = [i for i, item in enumerate(r_more) if re.search(regex, item)]
    if len(top_matches) == 0:
        issues.append("No registration status returned.")
        return registered_serials, registered_switches, issues
    top = top_matches[0]
    if debug:
        print(f"top = {top}")

    z = top
    while z < qty_switches + top:
        switch_result = r_more[z].split()
        if len(switch_result) < 7:
            issues.append("No registration status returned.")
            return registered_serials, registered_switches, issues
        registered_serials.append(switch_result[3])
        registered_switches.append(
            {
                "switch_num": switch_result[0],
                "PID": switch_result[1],
                "cat_serial": switch_result[2],
                "meraki_serial": switch_result[3],
                "mac_address": switch_result[4],
                "migration_status": switch_result[5],
                "mode": switch_result[6],
            }
        )
        z += 1
    if unified_os:
        if not MERAKI_DRY_RUN:
            r = net_connect.send_command_timing("conf t", strip_prompt=False, strip_command=False)
            if debug:
                print(r)
            r = net_connect.send_command_timing(
                mgmt_commands.no_connect_mgmt,
                strip_prompt=False,
                strip_command=False,
            )
            if debug:
                print(r)
        else:
            print(f"[DRY-RUN] Skipped: {mgmt_commands.no_connect_mgmt}")
    return registered_serials, registered_switches, issues


def Register(
    host_id,
    ios_username,
    ios_password,
    ios_port,
    ios_secret,
    inventory_by_mac: dict[str, dict],
):
    """
    This function will check a Catalyst IOSXE switch for compatibility with
    Meraki management prior to registering the switch (or stack) to Dashboard.
    Items checked include:
        - A stack of 1-8 switches
        - The version of IOSXE
        - An ip name-server
        - A layer-3 interface that is operational
        - A default route
        - Succesful results of Meraki registration
    ** Need to add show meraki compatibility check. **
    :param host_id: The switch or stack to SSH into
    :param ios_username: Username for SSH
    :param ios_password: Password for SSH
    :param ios_port: Port number for SSH
    :param ios_secret: IOSXE secret password for CLI escalation
    :param inventory_by_mac: Optional map from normalized base Ethernet MAC to
        Dashboard inventory device dict; from get_switch_inventory_by_mac().
        When omitted, inventory-based early return is skipped.
    :return: A string indicating success or failure to be used in reporting,
    :      : a list with any issues encountered, and lists of registered
    :      : switches, the Meraki serial numbers assigned, and a list of the
    :      : NM modules per switch for later.
    """

    debug = DEBUG or DEBUG_REGISTER
    registered_switches = list()
    registered_serials = list()
    already_claimed = False

    # SSH to the switch with netmiko, read the config, grab the hostname,
    # write the config out to a file using hostname as part of the filespec
    session_info = {
        "device_type": "cisco_xe",
        "host": host_id,
        "username": ios_username,
        "password": ios_password,
        "port": ios_port,  # optional, defaults to 22
        "secret": ios_secret,  # optional, defaults to ''
    }
    net_connect = ConnectHandler(**session_info)
    net_connect.enable()

    base_ethernet_macs, qty_switches, _ = get_base_ethernet_macs(net_connect)
    nm_list = GetNmList(net_connect=net_connect)

    precheck = prechecks(net_connect)
    issues = precheck.issues
    unified_os = precheck.unified_os

    # If we had any issues to this point, return with issues
    if len(issues) != 0:
        net_connect.disconnect()
        return (
            "unsuccessfully",
            issues,
            registered_switches,
            [],
            nm_list,
            unified_os,
            already_claimed,
        )

    registered_serials, already_claimed = get_existing_registration_serials(
        net_connect,
        inventory_by_mac,
        base_ethernet_macs,
        debug,
    )
    if len(registered_serials) > 0:
        net_connect.disconnect()
        return (
            "successfully",
            issues,
            registered_switches,
            registered_serials,
            nm_list,
            unified_os,
            already_claimed,
        )

    registered_serials, registered_switches, reg_issues = register_stack_for_cloud_ids(
        net_connect, unified_os, qty_switches, debug
    )
    if len(reg_issues) != 0:
        net_connect.disconnect()
        return (
            "unsuccessfully",
            reg_issues,
            registered_switches,
            [],
            nm_list,
            unified_os,
            already_claimed,
        )
    net_connect.disconnect()
    if debug:
        print(
            "successfully",
            issues,
            registered_switches,
            registered_serials,
            nm_list,
            unified_os,
            already_claimed,
        )
    return (
        "successfully",
        issues,
        registered_switches,
        registered_serials,
        nm_list,
        unified_os,
        already_claimed,
    )
