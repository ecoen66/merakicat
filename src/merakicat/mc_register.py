from netmiko import ConnectHandler
from mc_user_info import DEBUG, DEBUG_REGISTER
from mc_get_nms import GetNmList
import re


def Register(host_id, ios_username, ios_password, ios_port, ios_secret):
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
    :return: A string indicating success or failure to be used in reporting,
    :      : a list with any issues encountered, and lists of registered
    :      : switches, the Meraki serial numbers assigned, and a list of the
    :      : NM modules per switch for later.
    """

    debug = DEBUG or DEBUG_REGISTER

    issues = list()
    registered_switches = list()
    registered_serials = list()
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
    nm_list = GetNmList(host_id, ios_username,
                          ios_password, ios_port, ios_secret)

    # Check the version of IOSXE running on the switch
    r = net_connect.send_command('show version').split("\n")
    version = r[0].split("Version")[1].strip()[:8]
    if debug:
        print(f"In Register, version = {version}")
    v = list(map(int, version.split('.')))
    if debug:
        print(f"In Register, v = {v}")
    if v[0] < 17:
        if v[1] < 10:
            if v[2] < 1:
                issues.append("IOSXE version {version} is less than 17.10.1")
        elif v[1] == 13 and v[2] == 1:
            issues.append("There is a known issue registering to " +
                          "Dashboard from IOSXE 17.13.1")

    # Check that the "Before you Begin" features are configured

    #  ip name-server
    r = net_connect.send_command('show ip name-servers')
    if len(r) == 16 and r[0:15] == '255.255.255.255':
        issues.append("No ip name-server found.")

    #  interface vlan {vlan-id}
    #   ip address
    #   <no shutdown>
    r = net_connect.send_command('show ip int brief | include Vlan')
    r_more = r.split("\n")
    x = 0
    good_vlans = 0
    while x <= len(r_more)-1:
        vlan, ip, ok, method, status, protocol = r_more[x].split()
        if not ip == "unassigned" and status == "up" and protocol == "up":
            good_vlans += 1
        x += 1
    if good_vlans == 0:
        issues.append("No L3 interface found.")

    #  ip default-gateway  == OR == ip route 0.0.0.0 0.0.0.0
    r = net_connect.send_command('show ip route 0.0.0.0')
    if r == "% Network not in table":
        issues.append("No default route found.")

    # With that out of the way, we can check meraki compatibility
    r = net_connect.send_command('show meraki compatibility')
    r_more = r.split("\n")

    # Check Boot Mode
    if not r_more[3].find("Incompatible") == -1:
        issues.append("Boot mode must be set to INSTALL.")
        if debug:
            print("Boot mode must be set to INSTALL.")

    # Check the line for each switch
    lines_to_test = len(r_more) - 14
    x = 0
    if debug:
        print(f"lines_to_test = {lines_to_test}, x = {x}")
    while x <= lines_to_test:
        if debug:
            print(f"Testing: {r_more[x+7]}")

        # Check a switch line to see if the word Incompatible shows up
        res = [i for i in range(len(r_more[x+7]))
               if r_more[x+7].startswith(" - Incompatible", i)]
        if not len(res) == 0:

            # It did... not sure how many times...
            bad_switch = r_more[x+7].split()[0]
            issues.append("Issues with switch " + bad_switch + ":")
            if debug:
                print("Issues with switch " + bad_switch + ":")

            # We will loop for the number of times that "Incompatible"
            # shows up on the switch line
            y = 0
            while y < len(res):
                offense = r_more[x+7]

                # If "Incompatible" shows up before character 50...
                # then it is an issue with the switch model
                if res[y] < 50:
                    details = offense[:res[y]].strip().split()[1]
                    if debug:
                        print("  Switch Model = " + details)
                    issues.append("  Switch Model = " + details)
                else:
                    details = offense[res[y-1]+15:res[y]].strip()

                    # If "Incompatible" shows up past character 80...
                    # then it is an issue with the NM model
                    if res[y] > 80:
                        if debug:
                            print("  NM Module Model = " + details)
                        issues.append("  NM Module Model = " + details)
                    else:

                        # Otherwise, it is an issue with the Bootloader
                        if debug:
                            print("  Bootloader Version = " + details)
                        issues.append("  Bootloader Version = " + details)
                y += 1
        x += 1

    # If we had any issues to this point, return with issues
    if not len(issues) == 0:
        net_connect.disconnect()
        return "unsuccessfully", issues, registered_switches, [], nm_list

    # Register all switches in the stack to the Meraki Dashboard
    # net_connect.enable()
    r = net_connect.send_command_timing('service meraki register switch all',
                                        strip_prompt=False,
                                        strip_command=False)
    if debug:
        print(r)
    if not r.find("Are you sure") == -1:
        r = net_connect.send_command_timing('yes',
                                            strip_prompt=False,
                                            strip_command=False)
        if debug:
            print(r)
    net_connect.disconnect()

    # Add logic to parse for issues in Conversion Status column
    #
    #

    top = -1
    bottom = -1

    r_more = r.split("\n")
    if debug:
        print(f"r_more = {r_more}")

    # Find the first line number (top) of the results table in the output
    regex = re.compile("^1")
    top = [i for i, item in enumerate(r_more) if re.search(regex, item)][0]

    # If there were no lines in the results, then we've got a problem...
    if top == -1:
        return ("unsuccessfully", ["No registration status returned."],
                registered_switches, nm_list)
    if debug:
        print(f'top = {top}')

    # Find the "Please note..."" line number (y) below the table in the output
    regex = re.compile("^Please note")
    bottom = [i for i, item in enumerate(r_more) if re.search(regex, item)][0]
    if debug:
        print(f'bottom = {bottom}')

    # Adjust to the last line of the final results table in the output
    bottom -= 2

    # Otherwise, translate the results table into a list of dictionaries -
    # (one dict per switch) and return that with a success flag
    z = top
    while z <= bottom:
        switch_result = r_more[z].split()
        registered_serials.append(switch_result[3])
        registered_switches.append({
            'switch_num': switch_result[0],
            'PID': switch_result[1],
            'cat_serial': switch_result[2],
            'meraki_serial': switch_result[3],
            'mac_address': switch_result[4],
            'migration_status': switch_result[5],
            'mode': switch_result[6]
        })
        z += 1
    if debug:
        print("successfully", issues, registered_switches,
              registered_serials, nm_list)
    return ("successfully", issues, registered_switches,
            registered_serials, nm_list)
