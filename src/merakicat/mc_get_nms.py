from typing import Any

from netmiko import ConnectHandler

try:
    from mc_user_info import DEBUG
except ImportError:
    DEBUG = False


def GetNmList(
    host_id: str | None = None,
    ios_username: str | None = None,
    ios_password: str | None = None,
    ios_port: int | None = None,
    ios_secret: str | None = None,
    *,
    net_connect: Any | None = None,
) -> list[str]:
    """Collect NM uplink module models for each switch in a stack."""
    if net_connect is not None and host_id is not None:
        raise ValueError("Pass either net_connect or host_id, not both")
    if net_connect is None and host_id is None:
        raise ValueError("Pass either net_connect or host_id")

    debug = DEBUG

    own_connection = net_connect is None
    if own_connection:
        if (
            ios_username is None
            or ios_password is None
            or ios_port is None
            or ios_secret is None
        ):
            raise ValueError(
                "ios_username, ios_password, ios_port, and ios_secret are required"
            )
        session_info = {
            "device_type": "cisco_xe",
            "host": host_id,
            "username": ios_username,
            "password": ios_password,
            "port": ios_port,
            "secret": ios_secret,
        }
        net_connect = ConnectHandler(**session_info)
        net_connect.enable()

    nm_list: list[str] = []

    # Grab the switches in the stack
    r = str(net_connect.send_command("show switch"))
    qty_switches = len(r.split("\n")) - 8

    # Grab the uplink module in each switch
    x = 1
    while x <= qty_switches:
        r = str(
            net_connect.send_command(
                'show inventory "Switch ' + str(x) + ' FRU Uplink Module 1"'
            )
        )
        if debug:
            print(f"For switch {x}, r = {r}")
        if debug:
            print(f"For switch {x}, len(r) = {len(r)}")
        if not r[0] == "%":
            nm_list.append(r.split("\n")[1].split()[1])
        else:
            nm_list.append("")
        x += 1
    if debug:
        print(f"For the {qty_switches} switches in the stack, " +
              f"the NM modules are {nm_list}")
    if own_connection:
        net_connect.disconnect()
    return nm_list
