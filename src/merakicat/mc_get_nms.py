from netmiko import ConnectHandler
from mc_user_info import DEBUG
import re


def GetNmList(host_id, ios_username, ios_password, ios_port, ios_secret):
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
    :param host: The switch or stack to SSH into
    :param username: Username for SSH
    :param password: Password for SSH
    :param port: Port number for SSH
    :param secret: IOSXE secret password for CLI escalation
    :return: A list of NM modules for all switches in the stack
    """

    debug = DEBUG

    nm_list = list()

    # SSH to the switch with netmiko, read the config, grab the hostname,
    # write the config out to a file using hostname as part of the filespec
    session_info = {
        'device_type': 'cisco_xe',
        'host': host_id,
        'username': ios_username,
        'password': ios_password,
        'port': ios_port,         # optional, defaults to 22
        'secret': ios_secret,     # optional, defaults to ''
    }
    net_connect = ConnectHandler(**session_info)
    net_connect.enable()
    switch_name = net_connect.find_prompt()
    switch_name = switch_name[:len(switch_name) - 1]

    # Grab the switches in the stack
    r = net_connect.send_command('show switch')
    qty_switches = len(r.split("\n"))-8

    # Grab the uplink module in each switch
    x = 1
    while x <= qty_switches:
        r = net_connect.send_command('show inventory "Switch ' +
                                     str(x) + ' FRU Uplink Module 1"')
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
    net_connect.disconnect()
    return(nm_list)