'''
#####################################################################################

This dictionary contains many Meraki switch & port configuration elements,
along with their CiscoConfParse IOSXE parsing matches, and the values to
pass back for the element.

Each element is the name of a switch_dict or port_dict key.

There are currently three sub-dictionaries: 'switch', 'downlink' & 'uplink'.

#####################################################################################

Elements in the 'switch' sub-dictionary have two keys within them: 'iosxe' & 'meraki'.

The 'iosxe' value is the python code (as a string) to extract information from the
switch config and set a value based on that information.

The 'meraki' value is the python code (as a string) to do something with that value,
and return one or more key:value pairs to add to a returns_dict for later use.

#####################################################################################

Elements in the 'downlink' & 'uplink' sub-dictionaries have three keys within them:
'iosxe', 'regex' & 'meraki'.

The 'regex' value is the CiscoConfParse IOSXE parsing regex match for this element.

The 'iosxe' value is the python code (as a string) to extract information from the
switch config and set a value based on that information.

The 'meraki' value is a sub-dictionary that contains up to 3 entries:
'skip', 'default' and OPTIONALLY 'post-process'.

The 'skip' value indicates whether or not to add this element to the meraki config,
or to do some post-processing for the meraki config.
    Examples include 'speed' & 'duplex', which have no direct
    relation to meraki config elements.

The 'default' value indicates the value to set for this port if there was no match
in the IOSXE config for the port.

The 'post-process' value is the python code (as a string) to execute to provide a
generated value for the element in the meraki config loop.
    An example would be 'linkNegotiation' which must be
    determined based on a combination of 'speed' & 'duplex'.

#####################################################################################
'''


config_pedia = {
    
    'switch': {
        
        'switch_name': {
            'iosxe': "\
\
switch_name = ''\n\
switch_name_obj = parse.find_objects('^hostname')\n\
if not switch_name_obj == []:\n\
    switch_name = switch_name_obj[0].re_match_typed('^hostname\s(\S+)')\n\
if switch_name == '':\n\
    switch_name = 'Switch'\n\
if debug:\n\
    print(f'switch_name = {switch_name}')\n",
            
            'meraki': "\
\
urls = list()\n\
blurb = 'This was a conversion from a Catalyst IOSXE config.'\n\
n = 0\n\
if debug:\n\
    print(f'dir() = {dir()}')\n\
switch_name = switch_dict['switch_name']\n\
if switch_name == '':\n\
    switch_name = 'Switch'\n\
if len(sw_list) == 1:\n\
    try:\n\
        ## Set the switch name and notes\n\
        response = dashboard.devices.updateDevice(sw_list[n], name=switch_name, notes=blurb)\n\
        urls.append(response['url'])\n\
        if debug:\n\
            print(f'Dashboard response was: {response}')\n\
    except:\n\
        print(f'Unable to configure name on switch.')\n\
else:\n\
    while n <= len(sw_list)-1:\n\
        try:\n\
            ## Set the switch name and notes\n\
            response = dashboard.devices.updateDevice(sw_list[n], name=switch_name+'-'+str(n+1), notes=blurb)\n\
            urls.append(response['url'])\n\
            networkId = response['networkId']\n\
            if debug:\n\
                print(f'Dashboard response was: {response}')\n\
        except:\n\
            print('Cannot set the switch name for switch ' + switch_name+'-'+str(n+1))\n\
        n +=1\n\
    if debug:\n\
        print(f'networkId = {networkId}')\n\
    try:\n\
        ## Create the switch stack\n\
        response = dashboard.switch.createNetworkSwitchStack(networkId=networkId, serials=sw_list, name=switch_name)\n\
        if debug:\n\
            print(f'Dashboard response to Create Stack was: {response}')\n\
        # Oops, we got a Dashboard ERROR while claiming the switches to the network\n\
    except Exception as e:\n\
        if debug:\n\
            print(f'Meraki API error: {e}')\n\
            print(f'status code = {e.status}')\n\
            print(f'reason = {e.reason}')\n\
            print(f'error = {e.message}')\n\
        if not e.message['errors'][0] == 'Cannot stack switches that are already part of a switch stack':\n\
            print(f'Cannot create switch stack {switch_name} with {sw_list}.')\n\
return_vals = ['urls']\n\
if debug:\n\
    print(f'dir() = {dir()}')\n"}
    },
    
    'downlink': {
        
        'name': {
            'iosxe': "\
\
if debug:\n\
    print(f'dir() = {dir()}')\n\
try:\n\
    name = child.re_match_typed(regex=r'\sdescription\s+(\S.+)')\n\
except:\n\
    pass\n",
            
            'regex': r'\sdescription\s+(\S.+)',
            
            'meraki': {
                'skip': False,
                'default': ''
            }
        },
        
        'speed': {
            'iosxe': "\
\
if debug:\n\
    print(f'dir() = {dir()}')\n\
try:\n\
    speed = child.re_match_typed(regex=r'\sspeed\s+(\S.*)')\n\
except:\n\
    pass\n",
            
            'regex': r'\sspeed\s+(\S.*)',
            
            'meraki': {
                'skip': True,
                'default': ''
            }
        },
        
        'duplex': {
            'iosxe': "\
\
if debug:\n\
    print(f'dir() = {dir()}')\n\
try:\n\
    duplex = child.re_match_typed(regex=r'\sduplex\s+(\S.+)')\n\
except:\n\
    pass\n",
            
            'regex': r'\sduplex\s+(\S.+)',
            
            'meraki': {
                'skip': True,
                'default': ''
            }
        },
        
        'linkNegotiation': {
            'iosxe': "",
            'regex': '',
            'meraki': {
                'skip': 'post-process',
                'post-process': "\
\
linkNegotiation = ''\n\
try:\n\
    speed = int(m['speed'])\n\
    if speed < 1000:\n\
        linkNegotiation += str(speed)+' Megabit '\n\
    else:\n\
        linkNegotiation += str(int(speed/1000))+' Gigabit '\n\
    try:\n\
        duplex = m['duplex']\n\
        match duplex:\n\
            case 'half':\n\
                linkNegotiation += 'half duplex (forced)'\n\
            case 'full':\n\
                linkNegotiation += 'full duplex (forced)'\n\
    except KeyError:\n\
        linkNegotiation += '(auto)'\n\
except:\n\
    linkNegotiation = 'Auto negotiate'\n",
                'default': 'Auto negotiate'
            }
        },
        
        'type': {
            'iosxe': "\
\
if debug:\n\
    print(f'dir() = {dir()}')\n\
try:\n\
    type = child.re_match_typed(regex=r'\sswitchport\smode\s+(\S.+)')\n\
except:\n\
    pass\n",
            
            'regex': r'\sswitchport\smode\s+(\S.+)',
            
            'meraki': {
                'skip': False,
                'default': 'trunk'
            }
        },
        
        'poeEnabled': {
            'iosxe': "\
\
if debug:\n\
    print(f'dir() = {dir()}')\n\
try:\n\
    poeEnabled = not child.re_match_typed(regex=r'\spower\sinline\s+(\S.+)')=='never'\n\
except:\n\
    pass\n",
            
            'regex': r'\spower\sinline\s+(\S.+)',
            
            'meraki': {
                'skip': False,
                'default': True
            }
        },
        
        'allowedVlans': {
            'iosxe': "\
\
if debug:\n\
    print(f'dir() = {dir()}')\n\
try:\n\
    allowedVlans = child.re_match_typed(regex=r'\sswitchport\strunk\sallowed\svlan\s+(\S.*)')\n\
    if debug:\n\
        print(f'allowedVlans = {allowedVlans}')\n\
except:\n\
    pass\n",
            
            'regex': r'\sswitchport\strunk\sallowed\svlan\s+(\S.*)',
            
            'meraki': {
                'skip': False,
                'default': '1-1000'
            }
        },
        
        'vlan': {
            
            'iosxe': "\
\
if debug:\n\
    print(f'dir() = {dir()}')\n\
try:\n\
    vlan = child.re_match_typed(regex=r'\sswitchport\svlan\s+(\S.*)')\n\
except:\n\
    pass\n\
try:\n\
    vlan = child.re_match_typed(regex=r'\sswitchport\strunk\snative\svlan\s+(\S.*)')\n\
except:\n\
    pass\n",
            
            'regex': r'\sswitchport\svlan\s+(\S.*)',
            
            'meraki': {
                'skip': False,
                'default': '1'
            }
        },
        
        'vlan': {
            
            'iosxe': "\
\
if debug:\n\
    print(f'dir() = {dir()}')\n\
try:\n\
    vlan = child.re_match_typed(regex=r'\sswitchport\strunk\snative\svlan\s+(\S.*)')\n\
except:\n\
    pass\n",
            
            'regex': r'\sswitchport\strunk\snative\svlan\s+(\S.*)',
            
            'meraki': {
                'skip': False,
                'default': '1'
            }
        },
        
        'voiceVlan': {
            
            'iosxe': "\
\
if debug:\n\
    print(f'dir() = {dir()}')\n\
voiceVlan = child.re_match_typed(regex=r'\sswitchport\svoice\svlan\s+(\S.*)')\n",
            
            'regex': r'\sswitchport\svoice\svlan\s+(\S.*)',
            
            'meraki': {
                'skip': False,
                'default': None
            }
        }
    },
    
    'uplink': {
    }
}

def index_config_pedia():
    print("\n\n=====================")
    print("Index of config_pedia:")
    print("=====================\n")
    for key,value in config_pedia.items():
        print(key+":\n")
        for k,v in value.items():
            print(" - "+k+"\n")

if __name__ == '__main__':
    index_config_pedia()
