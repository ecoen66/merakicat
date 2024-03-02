import meraki
import re
from mc_user_info import *

def Claim(dashboard,dest_net,serials):
    """
    This function will claim a set of Meraki network device serial numbers to Meraki
    network.
    :param dashboard: The active Meraki dashboard API session to use
    :param dest_net: The destination Meraki network to claim the devices to
    :param serials: The serial number of the Meraki network devices to claim
    :return: A string with any issues encountered, and lists of devices that could not be
    :      :  claimed, claimed devices, already claimed devices
    """
    
    debug = DEBUG or DEBUG_CLAIM
    
    issues = ""
    claimed_switches = serials
    ac_switches =list()
    bad_switches =list()
    
    '''
    Some example meraki.APIError responses in meraki.APIError.message:
    
    
    Example of 2 switches to register, both already claimed in another network:
        claim XXXX-XXXX-XXXX,YYYY-YYYY-YYYY to MyNet
    {'errors': [
        'Device with serial XXXX-XXXX-XXXX is already claimed and in NotMyNetwork (network ID: L_NNNNNNNNNNNNNNNNNN)',
        'Device with serial YYYY-YYYY-YYYY is already claimed and in NotMyNetwork (network ID: L_NNNNNNNNNNNNNNNNNN)'
    ]}
    
    Example of 2 switches to register, one is not found and one is already claimed in requested network:
        claim XXXX-XXXX-XXXX,ZZZZ-ZZZZ-ZZZZ to MyNet
    {'errors': [
      'Device with serial XXXX-XXXX-XXXX not found',
      'Device with serial ZZZZ-ZZZZ-ZZZZ is already claimed and in MyNet (network ID: L_OOOOOOOOOOOOOOOOOO)'
    ]}
    '''

    try:
        r = (dashboard.networks.claimNetworkDevices(networkId=dest_net,serials=serials))
        if debug:
            print(f"issues from Dashboard for claiming switches was:\n{r}")
    # Oops, we got a Dashboard ERROR while claiming the switches to the network
    except meraki.APIError as e:
        if debug:
            print(f'Meraki API error: {e}')
            print(f'status code = {e.status}')
            print(f'reason = {e.reason}')
            print(f'error = {e.message}')
        # Let's parse through the list of errors returned and divide them
        # into Already Claimed and Not Found
        x=0
        while x <= len(e.message['errors'])-1:
            # If it is already claimed... 
            if re.search('already claimed', e.message['errors'][x]):
                if debug:
                    print(e.message['errors'][x].split("Device with serial")[1].split()[0])
                ac_switch = e.message['errors'][x].split("Device with serial")[1].split()[0]
                if debug:
                    print(e.message['errors'][x].split("already claimed and in "))
                    print(e.message['errors'][x].split("already claimed and in ")[1])
                    print(e.message['errors'][x].split("already claimed and in ")[1].split('(')[0])
                ac_net_name = e.message['errors'][x].split("already claimed and in ")[1].split("(")[0]
                if debug:
                    print(e.message['errors'][x].split("already claimed and in ")[1].split("network ID: ")[1].split(')')[0])
                # If it is already claimed but in a different network
                # remove it from the claimed_switches list
                # append it to the bad_switches list
                # append a ERROR to the issues string
                #if not (e.message['errors'][x].split("already claimed and in ")[1].split("network ID: ")[1].split(')')[0]) == dest_net:
                if not (e.message['errors'][x].split("already claimed and in ")[1].split("network ID: ")[1].split(')')[0]) == dest_net:
                    issues +="ERROR: Switch {} has already been claimed and is in the {} network.\n".format(ac_switch, ac_net_name)
                    claimed_switches.remove(ac_switch)
                    bad_switches.append(ac_switch)
                # If it is already claimed in the desired network 
                # remove it from the claimed_switches list
                # append it to the ac_switches list and append a WARNING to the issues string
                else:
                    issues +="Warning: Switch {} has already been claimed in that network.\n".format(ac_switch)
                    ac_switches.append(ac_switch)
            
            # If it is not found, append it to the bad_switches list
            # remove it from the claimed_switches list
            # append a ERROR to the issues string
            elif re.search('not found', e.message['errors'][x]):
                if debug:
                    print(e.message['errors'][x].split("Device with serial")[1].split()[0])
                bad_switch = e.message['errors'][x].split("Device with serial")[1].split()[0]
                bad_switches.append(bad_switch)
                claimed_switches.remove(bad_switch)
                issues +="Error: Switch {} was not found.\n".format(bad_switch)
            x+=1
        if debug:
            print(f"claimed_switches = {claimed_switches}")
            print(f"ac_switches = {ac_switches}")
            print(f"bad_switches = {bad_switches}")
        # Even though we got an error, keep on going...
        pass
    return(issues,bad_switches,ac_switches,claimed_switches)