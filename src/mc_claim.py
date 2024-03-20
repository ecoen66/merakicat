import meraki
import re
from mc_user_info import DEBUG, DEBUG_CLAIM


def Claim(dashboard, dest_net, serials):
    """
    This function will claim a set of Meraki network device serial numbers
    to a Meraki network.
    :param dashboard: The active Meraki dashboard API session to use
    :param dest_net: The destination Meraki network to claim the devices to
    :param serials: The serial numbers of the Meraki network devices to claim
    :return: A string with any issues encountered, and lists of devices that
    :      : could not be claimed, claimed devices, already claimed devices
    """

    debug = DEBUG or DEBUG_CLAIM

    issues = ""
    claimed_switches = serials
    ac_switches = list()
    bad_switches = list()

    for serial in serials:
        try:
            r = (dashboard.networks.removeNetworkDevices(
                 networkId=dest_net, serial=serial))
        except meraki.APIError:
            pass
    try:
        r = (dashboard.networks.claimNetworkDevices(
             networkId=dest_net, serials=serials))
        if debug:
            print(f"issues from Dashboard for claiming switches was:\n{r}")
    # Oops, we got a Dashboard ERROR while claiming switches to the network
    except meraki.APIError as e:
        if debug:
            print(f'Meraki API error: {e}')
            print(f'status code = {e.status}')
            print(f'reason = {e.reason}')
            print(f'error = {e.message}')
        # Let's parse through the list of errors returned and divide them
        # into Already Claimed and Not Found
        x = 0
        while x <= len(e.message['errors'])-1:
            # If it is already claimed...
            if re.search('already claimed', e.message['errors'][x]):
                if debug:
                    print(e.message['errors'][x].split(
                          "Device with serial")[1].split()[0])
                ac_switch = e.message['errors'][x].split(
                    "Device with serial")[1].split()[0]
                if debug:
                    print(e.message['errors'][x].split(
                          "already claimed and in ")[1].split('(')[0])
                ac_net_name = e.message['errors'][x].split(
                    "already claimed and in ")[1].split("(")[0]
                if debug:
                    print(e.message['errors'][x].split(
                          "already claimed and in ")[1].split(
                          "network ID: ")[1].split(')')[0])
                # If it is already claimed but in a different network
                # remove it from the claimed_switches list
                # append it to the bad_switches list
                # append a ERROR to the issues string
                if not (e.message['errors'][x].split(
                    "already claimed and in ")[1].split(
                        "network ID: ")[1].split(')')[0]) == dest_net:
                    issues += "ERROR: Switch "+ac_switch+" has already "
                    issues += "been claimed and is in the "+ac_net_name
                    issues += " network.\n"
                    claimed_switches.remove(ac_switch)
                    bad_switches.append(ac_switch)
                # If it is already claimed in the desired network
                # remove it from the claimed_switches list and append it to
                # ac_switches list and append a WARNING to the issues string
                else:
                    issues += "Warning: Switch "+ac_switch+" has already "
                    issues += "been claimed in that network.\n"
                    ac_switches.append(ac_switch)
            # If it is not found, append it to the bad_switches list
            # remove it from the claimed_switches list and
            # append a ERROR to the issues string
            elif re.search('not found', e.message['errors'][x]):
                if debug:
                    print(e.message['errors'][x].split(
                        "Device with serial")[1].split()[0])
                bad_switch = e.message['errors'][x].split(
                    "Device with serial")[1].split()[0]
                bad_switches.append(bad_switch)
                claimed_switches.remove(bad_switch)
                issues += "Error: Switch "+bad_switch+" was not found.\n"
            x += 1
        if debug:
            print(f"claimed_switches = {claimed_switches}")
            print(f"ac_switches = {ac_switches}")
            print(f"bad_switches = {bad_switches}")
        # Even though we got an error, keep on going...
        pass
    return (issues, bad_switches, ac_switches, claimed_switches)
