import meraki
import re
try:
    from mc_user_info import DEBUG, DEBUG_CLAIM
except ImportError:
    DEBUG = DEBUG_CLAIM = False


def Claim(dashboard, dest_net, serials, ios_username, ios_password, ios_secret):
    """
    This function will claim a set of Meraki network device serial numbers
    to a Meraki network.
    :param dashboard: The active Meraki dashboard API session to use
    :param dest_net: The destination Meraki network to claim the devices to
    :param serials: The serial numbers of the Meraki network devices to claim
    :param ios_username: Username for SSH from Dashboard
    :param ios_password: Password for SSH from Dashboard
    :param ios_secret: IOSXE secret password for CLI escalation
    :return: A string with any issues encountered, and lists of devices that
    :      : could not be claimed, claimed devices, already claimed devices
    """

    debug = DEBUG or DEBUG_CLAIM

    issues = ""
    claimed_switches = serials
    ac_switches = list()
    bad_switches = list()

    try:
        r = dashboard.switch.getNetworkSwitchStacks(networkId=dest_net)
        if debug:
            print(f"I grabbed the list of switch stacks in network {dest_net}, it was {r}")
        for stack in r:
            for serial in serials:
                if serial in stack['serials'][0]:
                    try:
                        response = dashboard.switch.deleteNetworkSwitchStack(dest_net,stack['id'])
                        if debug:
                            print(f"I deleted switch stack {stack['id']}, with switch {serial}")
                        break
                    except meraki.APIError as e:
                        if debug:
                            print(f"In an attempt to delete switch stack {stack['id']}, we encountered the following error:")
                            print(f'Meraki API error: {e}')
                            print(f'status code = {e.status}')
                            print(f'reason = {e.reason}')
                            print(f'error = {e.message}')
                        continue
    except meraki.APIError as e:
        if debug:
            print(f"In an attempt to get the list of switch stacks for network {dest_net}, we encountered the following error:")
            print(f'Meraki API error: {e}')
            print(f'status code = {e.status}')
            print(f'reason = {e.reason}')
            print(f'error = {e.message}')

    for serial in serials:
        try:
            r = (dashboard.networks.removeNetworkDevices(
                 networkId=dest_net, serial=serial))
            if debug:
                print(f"I deleted serial number {serial}.")
        except meraki.APIError as e:
            if debug:
                print(f"In an attempt to delete serial number {serial}, we encountered the following error:")
                print(f'Meraki API error: {e}')
                print(f'status code = {e.status}')
                print(f'reason = {e.reason}')
                print(f'error = {e.message}')
            continue

    # x = 0
    #while x <= len(serials)-1:
    for serial in serials:
        try:
            r = (dashboard.networks.claimNetworkDevices(
                 networkId=dest_net, serials=[serial], detailsByDevice=[
                   {
                    "serial": serial,
                    "details": [
                      {
                        "name": "username",
                        "value": ios_username
                      },
                      {
                        "name": "password",
                        "value": ios_password
                      },
                      {
                        "name": "enable password",
                        "value": ios_secret
                      }
                    ]
                   }
                 ]
                )
            )

            if debug:
                print(f"issues from Dashboard for claiming switch {serial} was:\n{r}")
        # Oops, we got a Dashboard ERROR while claiming switches to the network
        except meraki.APIError as e:
            if debug:
                print(f'Meraki API error: {e}')
                print(f'status code = {e.status}')
                print(f'reason = {e.reason}')
                print(f'error = {e.message}')
            # Let's parse through the list of errors returned and divide them
            # into Already Claimed and Not Found
            # If it is already claimed...
            if re.search('Devices already claimed', e.message['errors'][0]):
                ac_switch = serial

                # If it is already claimed in the desired network
                # remove it from the claimed_switches list and append it to
                # ac_switches list and append a WARNING to the issues string
                issues += "Warning: Switch "+ac_switch+" has already "
                issues += "been claimed in that network.\n"
                ac_switches.append(ac_switch)

            # If it is not found, append it to the bad_switches list
            # remove it from the claimed_switches list and
            # append a ERROR to the issues string
            elif re.search('not found', e.message['errors'][0]):
                bad_switch = serial
                bad_switches.append(serial)
                claimed_switches.remove(bad_switch)
                issues += "Error: Switch "+bad_switch+" was not found.\n"
            # Even though we got an error, keep on going...
        finally:
            if debug:
                print(f"claimed_switches = {claimed_switches}")
                print(f"ac_switches = {ac_switches}")
                print(f"bad_switches = {bad_switches}")

    return (issues, bad_switches, ac_switches, claimed_switches)
