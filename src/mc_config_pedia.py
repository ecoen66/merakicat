config_pedia = {
    
    'switch': {
        
        'switch_name': {
            'iosxe': "switch_name = ''\n\
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
        response = dashboard.devices.updateDevice(sw_list[n], name=switch_name, notes=blurb)\n\
        urls.append(response['url'])\n\
        if debug:\n\
            print(f'Dashboard response was: {response}')\n\
    except:\n\
        print(f'Unable to configure name on switch.')\n\
else:\n\
    while n <= len(sw_list)-1:\n\
        try:\n\
            response = dashboard.devices.updateDevice(sw_list[n], name=switch_name+'-'+str(n+1), notes=blurb)\n\
            urls.append(response['url'])\n\
            if debug:\n\
                print(f'Dashboard response was: {response}')\n\
        except:\n\
            print('Cannot set the switch name for switch ' + switch_name+'-'+str(n+1))\n\
        n +=1\n\
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