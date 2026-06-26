import re
from dataclasses import dataclass
from typing import Any

try:
    from mc_user_info import DEBUG, DEBUG_REGISTER
except ImportError:
    DEBUG = DEBUG_REGISTER = False


@dataclass(frozen=True)
class PrecheckResult:
    """State collected by prechecks before inventory lookup."""

    issues: list[str]
    unified_os: bool


def parse_ios_version(net_connect: Any) -> tuple[list[int], str]:
    """Parse the IOS XE version from show version."""
    r = str(net_connect.send_command("show version")).split("\n")
    version_line = r[1] if len(r) > 1 else ""
    version_match = re.search(r"Version\s+([0-9A-Za-z.\-]+)", version_line)
    version = version_match.group(1).strip(",") if version_match else "0.0.0"
    v = [int(x) for x in re.findall(r"\d+", version)]
    while len(v) < 3:
        v.append(0)
    return v[:3], version


def unified_os_from_version(v: list[int]) -> bool:
    """Return whether the IOS XE version uses unified management."""
    if v[0] == 17 and v[1] == 15 and v[2] >= 1:
        return True
    if v[0] == 17 and v[1] > 15:
        return True
    if v[0] > 17:
        return True
    return False


def get_unified_os(net_connect: Any) -> bool:
    """Return whether the switch uses unified IOS XE management."""
    v, _version = parse_ios_version(net_connect)
    return unified_os_from_version(v)


def prechecks(net_connect: Any) -> PrecheckResult:
    """Run compatibility checks."""
    debug = DEBUG or DEBUG_REGISTER
    issues: list[str] = []

    v, version = parse_ios_version(net_connect)
    if debug:
        print(f"In Register, version = {version}")
    if debug:
        print(f"In Register, v = {v}")
    if v[0] < 17:
        if v[1] < 10:
            if v[2] < 1:
                issues.append(f"IOSXE version {version} is less than 17.10.1")
        elif v[1] == 13 and v[2] == 1:
            issues.append(
                "There is a known issue registering to "
                + "Dashboard from IOSXE 17.13.1"
            )
        elif v[1] == 15 and v[2] == 3:
            issues.append(
                "There is a known issue registering to "
                + "Dashboard from IOSXE 17.15.3"
            )196289728

    unified_os = unified_os_from_version(v)

    r = str(net_connect.send_command("show ip name-servers"))
    if len(r) == 16 and r[0:15] == "255.255.255.255":
        issues.append("No ip name-server found.")

    r = str(net_connect.send_command("show ip int brief | include Vlan"))
    r_more = r.split("\n")
    x = 0
    good_vlans = 0
    while x <= len(r_more) - 1:
        try:
            vlan, ip, ok, method, status, protocol = r_more[x].split()
        except:
            vlan, ip, ok, method, status, status2, protocol = r_more[x].split()
        if not ip == "unassigned" and status == "up" and protocol == "up":
            good_vlans += 1
        x += 1
    if good_vlans == 0:
        issues.append("No L3 interface found.")

    r = str(net_connect.send_command("show ip route 0.0.0.0"))
    if r == "% Network not in table":
        issues.append("No default route found.")

    r = str(net_connect.send_command("show meraki compatibility"))
    r_more = r.split("\n")

    if v[0] >= 17 and v[1] >= 15:
        if not r_more[6].find("Incompatible") == -1:
            issues.append("Boot mode must be set to INSTALL.")
            if debug:
                print("Boot mode must be set to INSTALL.")
    else:
        if not r_more[3].find("Incompatible") == -1:
            issues.append("Boot mode must be set to INSTALL.")
            if debug:
                print("Boot mode must be set to INSTALL.")

    found_sw_num = [item for item in r_more if "Switch#" in item]
    first_sw_line = r_more.index(found_sw_num[0]) + 2
    lines_to_test = len(r_more) - first_sw_line
    x = 0
    if debug:
        print(f"lines_to_test = {lines_to_test}, x = {x}")
    while x < lines_to_test:
        if debug:
            print(f"Testing: {r_more[x + first_sw_line]}")
        res = [
            i
            for i in range(len(r_more[x + first_sw_line]))
            if r_more[x + first_sw_line].startswith(" - Incompatible", i)
        ]
        if not len(res) == 0:
            bad_switch = r_more[x + first_sw_line].split()[0]
            issues.append("Issues with switch " + bad_switch + ":")
            if debug:
                print("Issues with switch " + bad_switch + ":")
            y = 0
            while y < len(res):
                offense = r_more[x + first_sw_line]
                if res[y] < 50:
                    details = offense[: res[y]].strip().split()[1]
                    if debug:
                        print("  Switch Model = " + details)
                    issues.append("  Switch Model = " + details)
                else:
                    details = offense[res[y - 1] + 15 : res[y]].strip()
                    if res[y] > 80:
                        if debug:
                            print("  NM Module Model = " + details)
                        issues.append("  NM Module Model = " + details)
                    else:
                        if debug:
                            print("  Bootloader Version = " + details)
                        issues.append("  Bootloader Version = " + details)
                y += 1
        x += 1

    return PrecheckResult(issues=issues, unified_os=unified_os)
