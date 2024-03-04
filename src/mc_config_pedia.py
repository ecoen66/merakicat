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
name = ''\n\
if debug:\n\
    print(f'dir() = {dir()}')\n\
try:\n\
    name = child.re_match_typed(regex=r'\sdescription\s+(\S.+)')\n\
except:\n\
    pass\n",
            
            'meraki': {
                'default': ''
            }
        },
        'type': {
            'iosxe': "\
\
type = 'trunk'\n\
if debug:\n\
    print(f'dir() = {dir()}')\n\
try:\n\
    type = child.re_match_typed(regex=r'\sswitchport\smode\s+(\S.+)')\n\
except:\n\
    type = 'trunk'\n",
            
            'meraki': {
                'default': 'trunk'
            }
        },
        
        'vlan': {
            
            'iosxe': "\
\
vlan = '1'\n\
if debug:\n\
    print(f'dir() = {dir()}')\n\
try:\n\
    vlan = child.re_match_typed(regex=r'\sswitchport\svoice\svlan\s+(\S.*)')\n\
except:\n\
    pass\n\
try:\n\
    vlan = child.re_match_typed(regex=r'\sswitchport\strunk\snative\svlan\s+(\S.*)')\n\
except:\n\
    pass\n",
            
            'meraki': {
                'default': '1'
            }
        },
        
        'voiceVlan': {
            
            'iosxe': "\
\
voiceVlan = None\n\
if debug:\n\
    print(f'dir() = {dir()}')\n\
try:\n\
    voiceVlan = child.re_match_typed(regex=r'\sswitchport\svoice\svlan\s+(\S.*)')\n\
except:\n\
    pass\n",
            
            'meraki': {
                'default': None
            }
        }
    },
    
    'uplink': {
    }
}