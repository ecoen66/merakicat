import sys

'''
#####################################################################################

This dictionary contains many Meraki switch & port configuration elements,
along with their CiscoConfParse IOSXE parsing matches, and the values to
pass back for the element.

It is used for both evaluating and reporting on the applicability of the
IOSXE configured features in a Meraki switch and the capability of this application
to translate the feature to Meraki, as well as in the actual translation.

Each element is the name of a switch_dict or port_dict key.

There are currently two sub-dictionaries: 'switch' '& 'port', covering features at
the switch-level and at the port-level.

        To print the entire index of this encyclopedia, or to print the index
        based on either supported and translatable items or both, enter:

                  python mc_pedia [support] [translatable]


#####################################################################################

Elements in each sub-dictionary has many keys within them:
'name', 'support', 'translatable', 'regex', 'iosxe', 'note', 'url' & 'meraki'.

The 'name' value is the name for this element used in reporting.

The 'support' value indicates whether or not Meraki provides support for this element.

The 'translatable' value indicates whether or not Meraki Cat currently provides
a translation for this element.

The 'regex' value is the CiscoConfParse IOSXE parsing regex match for this element.

The 'iosxe' value is the python code (as a string) to extract information from the
switch config and set a value based on that information.

The OPTIONAL 'note' value provides additional information regarding this feature being
unsupported by Meraki. This is used for reporting.

The OPTIONAL 'url' value provides a link to documentation for additional information for
this unsupported element -- also for reporting.

The 'meraki' value is a sub-dictionary that contains up to 3 entries:
'skip', 'default' and OPTIONALLY 'post-process'.

The 'skip' value indicates whether or not to add this element to the meraki config,
or to do some post-processing for the meraki config.
    Examples include 'speed' & 'duplex', which have no direct
    relation to meraki config elements.

The 'default' value indicates the value to set for this port if there was no match
in the IOSXE config for the port.

The OPTIONAL 'post-process' value is the python code (as a string) to execute to
provide a generated value for the element in the meraki config loop.
    An example would be 'linkNegotiation' which must be
    determined based on a combination of 'speed' & 'duplex'.

#####################################################################################
'''


mc_pedia = {
    
    'switch': {
        
        'switch_name': {
            'name': "Hostname",
            'support':"✓",
            'translatable':"✓",
            'regex': '^hostname',
            'iosxe': "\
\
switch_name = ''\n\
switch_name_obj = parse.find_objects('^hostname')\n\
if not switch_name_obj == []:\n\
    switch_name = switch_name_obj[0].re_match_typed('^hostname\s(\S+)',default='Switch')\n\
if switch_name == '':\n\
    switch_name = 'Switch'\n\
host_name = switch_name\n\
if debug:\n\
    print(f'switch_name = {switch_name}')\n",
            
            'meraki': {
                'skip': 'post-process',
                'default': 'Auto negotiate',
                'post-process': "\
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
    print(f'dir() = {dir()}')\n"
            }
        },
        
        'vtp':{
            'name': "VTP",
            'support':"",
            'translatable':"",
            'regex': '^vtp',
            'meraki': {
                'skip': True
            },
            'iosxe': "vtp = parse.find_objects('^vtp')\n",
            'url':"https://documentation.meraki.com/MS/Port_and_VLAN_Configuration/Integrating_the_MS_Access_Switch_into_a_Cisco_VTP_domain",
            'note':"Not required"
        },
        
        'mls':{
            'name': "QoS",
            'support':"",
            'translatable':"",
            'regex': '^mls',
            'meraki': {
                'skip': True
            },
            'iosxe': "mls = parse.find_objects('^mls')\n"
        },
        
        'rstp':{
            'name':"Spanning Tree RSTP",
            'support':"✓",
            'translatable':"✓",
            'regex': '^spanning-tree mode rapid-pvst',
            'meraki': {
                'skip': True
            },
            'iosxe': "rstp = parse.find_objects('^spanning-tree mode rapid-pvst')\n"
        },
        
        'spanning':{
            'name':"Spanning Tree",
            'support':"",
            'translatable':"",
            'regex': '^spanning-tree',
            'meraki': {
                'skip': True
            },
            'iosxe': "\
spanning = ''\n\
if parse.find_objects('^spanning-tree extend system-id') == '':\n\
    if parse.find_objects('^spanning-tree mode rapid-pvst') == '':\n\
        spanning = parse.find_objects('^spanning-tree\s+(\S.+)')\n",
            'url':"https://documentation.meraki.com/MS/Port_and_VLAN_Configuration/Configuring_Spanning_Tree_on_Meraki_Switches_(MS)",
            'note':"Only Supports RSTP"
        },
        
        'snmp':{
            'name': "SNMP",
            'support':"",
            'translatable':"",
            'regex': '^snmp',
            'meraki': {
                'skip': True
            },
            'iosxe':"snmp = parse.find_objects('^snmp')\n"
        },
        
        'logging_host':{
            'name': "Syslog",
            'support':"",
            'translatable':"",
            'regex': '^logging',
            'meraki': {
                'skip': True
            },
            'iosxe':"logging_host = parse.find_objects('^logging')\n"
        },
        
        'ntp':{
            'name':"NTP",
            'support':"",
            'translatable':"",
            'regex': '^ntp',
            'meraki': {
                'skip': True
            },
            'iosxe':"ntp = parse.find_objects('^ntp')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Configured by default"
        },
        
        'access_list':{
            'name': "Access-List",
            'support':"",
            'translatable':"",
            'regex': '^access-list',
            'meraki': {
                'skip': True
            },
            'iosxe': "access_list = parse.find_objects('^access-list')\n"
        },
        
        'extended_access_list':{
            'name': "Extended ACL",
            'support':"",
            'translatable':"",
            'regex': '^ip\saccess-list',
            'meraki': {
                'skip': True
            },
            'iosxe': "extended_access_list = parse.find_objects('^ip\saccess-list')\n"
        },
        
        'port_mirror':{
            'name': "Port mirroring",
            'support': "✓",
            'translatable':"",
            'regex': '^monitor',
            'meraki': {
                'skip': True
            },
            'iosxe': "port_mirror = parse.find_objects('^monitor')\n"
        },
        
        'aaa':{
            'name': "AAA",
            'support':"",
            'translatable':"",
            'regex': '^aaa',
            'meraki': {
                'skip': True
            },
            'iosxe': "aaa = parse.find_objects('^aaa')\n",
            'url':"https://documentation.meraki.com/General_Administration/Managing_Dashboard_Access/Managing_Dashboard_Administrators_and_Permissions",
            'note':"Built in Meraki dashboard"
        },
        
        'netflow':{
            'name': "NetFlow",
            'support':"",
            'translatable':"",
            'regex': '^flow\sexporter',
            'meraki': {
                'skip': True
            },
            'iosxe': "netflow = parse.find_objects('^flow\sexporter')\n",
            'url':"https://documentation.meraki.com/MX/Monitoring_and_Reporting/NetFlow_Overview",
            'note':"Currently supported on MX only"
        },
        
        'dhcp':{
            'name':"DHCP server",
            'support':"",
            'translatable':"",
            'regex': '^ip\sdhcp\spool',
            'meraki': {
                'skip': True
            },
            'iosxe':"dhcp = parse.find_objects('^ip\sdhcp\spool')\n"
        },
        
        'banner':{
            'name': "Banner",
            'support':"",
            'translatable':"",
            'regex': '^banner',
            'meraki': {
                'skip': True
            },
            'iosxe': "banner = parse.find_objects('^banner')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not required"
        },
        
        'radius':{
            'name':"radius",
            'support':"",
            'translatable':"",
            'regex': '^radius-server',
            'meraki': {
                'skip': True
            },
            'iosxe':"radius = parse.find_objects('^radius-server')\n"
        },
        
        'radius2':{
            'name':"radius",
            'support':"",
            'translatable':"",
            'regex': '^radius\sserver',
            'meraki': {
                'skip': True
            },
            'iosxe':"radius2 = parse.find_objects('^radius\sserver')\n"
        },
        
        'http_server':{
            'name': "HTTP server",
            'support':"",
            'translatable':"",
            'regex': '^ip\shttp',
            'meraki': {
                'skip': True
            },
            'iosxe': "http_server = parse.find_objects('^ip\shttp')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported"
        },
        
        'stack':{
            'name': "Stack",
            'support':"✓",
            'translatable':"✓",
            'regex': '^switch',
            'meraki': {
                'skip': True
            },
            'iosxe': "\
stack = parse.find_objects('^switch')\n\
if len(stack) == 1:\n\
    stack = []\n"
        },
        
        'mab_vlan_mac':{
            'name': "MAB VLAN MAC Auth",
            'support':"",
            'translatable':"",
            'regex': '^mab\srequest\sformat',
            'meraki': {
                'skip': True
            },
            'iosxe': "mab_vlan_mac = parse.find_objects('^mab\srequest\sformat')\n",
            'url':"https://documentation.meraki.com/MS/Access_Control/MS_Switch_Access_Policies_(802.1X)",
            'note':"MAB with RADIUS is supported"
        },
        
        'vlan':{
            'name': "Layer 2 VLAN",
            'support':"",
            'translatable':"",
            'regex': '^vlan',
            'meraki': {
                'skip': True
            },
            'iosxe': "vlan = parse.find_objects('^vlan')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Configured by default"
        },
        
        'vpms':{
            'name': "VPMS",
            'support':"",
            'translatable':"",
            'regex': '^vpms',
            'meraki': {
                'skip': True
            },
            'iosxe': "vpms = parse.find_objects('^vpms')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported as it is dated technology"
        },
        
        'uplinkfast':{
            'name': "STP Uplinkfast",
            'support':"",
            'translatable':"",
            'regex': '^spanning-tree\suplinkfast',
            'meraki': {
                'skip': True
            },
            'iosxe': "uplinkfast = parse.find_objects('^spanning-tree\suplinkfast')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported"
        },
        
        'backbonefast':{
            'name': "STP Backbonefast",
            'support':"",
            'translatable':"",
            'regex': '^spanning-tree\sbackbonefast',
            'meraki': {
                'skip': True
            },
            'iosxe': "backbonefast = parse.find_objects('^spanning-tree\sbackbonefast')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported"
        },
        
        'loopguard':{
            'name': "STP Loopguard",
            'support':"",
            'translatable':"",
            'regex': '^vpms',
            'meraki': {
                'skip': True
            },
            'iosxe': "loopguard = parse.find_objects('spanning-tree\sloopguard')\n",
            'note':"Supported at the port level"
        },
        
        'dhcp_snooping':{
            'name': "DHCP Snooping",
            'support':"",
            'translatable':"",
            'regex': '^ip\sdhcp\ssnooping',
            'meraki': {
                'skip': True
            },
            'iosxe': "dhcp_snooping = parse.find_objects('ip\sdhcp\ssnooping')\n",
            'note':"Not Supported"
        },
        
        'ip_source_guard':{
            'name': "IP Source Binding",
            'support':"",
            'translatable':"",
            'regex': '^ip\ssource\sbinding',
            'meraki': {
                'skip': True
            },
            'iosxe': "ip_source_guard = parse.find_objects('ip\ssource\sbinding')\n"
        },
        
        'arp_inspection':{
            'name': "ARP Inspection",
            'support':"",
            'translatable':"",
            'regex': '^ip\sarp\sinspection',
            'meraki': {
                'skip': True
            },
            'iosxe': "arp_inspection = parse.find_objects('^ip\sarp\sinspection')\n"
        },
        
        'arp_acl':{
            'name': "ARP Access-list",
            'support':"",
            'translatable':"",
            'regex': '^arp\saccess-list',
            'meraki': {
                'skip': True
            },
            'iosxe': "arp_acl = parse.find_objects('^arp\saccess-list')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported"
        },
        
        'psp':{
            'name': "Protocol Storm Protection",
            'support':"",
            'translatable':"",
            'regex': '^psp',
            'meraki': {
                'skip': True
            },
            'iosxe': "psp = parse.find_objects('^psp')\n",
            'url': "https://documentation.meraki.com/MS",
            'note':"Not Supported"
        },
        
        'udld':{
            'name': "UDLD",
            'support':"",
            'translatable':"",
            'regex': '^udld',
            'meraki': {
                'skip': True
            },
            'iosxe': "udld = parse.find_objects('^udld')\n",
            'note':"Supported at the port level"
        },
        
        'logging':{
            'name': "Logging",
            'support':"",
            'translatable':"",
            'regex': '^logging',
            'meraki': {
                'skip': True
            },
            'iosxe': "logging = parse.find_objects('^logging')\n"
        },
        
        'ip_sla':{
            'name': "IP SLA",
            'support':"",
            'translatable':"",
            'regex': '^ip\ssla',
            'meraki': {
                'skip': True
            },
            'iosxe': "ip_sla = parse.find_objects('^ip\ssla')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported"
        },
        
        'multicast_igmp':{
            'name': "Multicast IGMP",
            'support':"",
            'translatable':"",
            'regex': '^ip\sigm',
            'meraki': {
                'skip': True
            },
            'iosxe': "multicast_igmp = parse.find_objects('^ip\sigmp')\n"
        },
        
        'multicast_pim':{
            'name': "Multicast PIM",
            'support':"",
            'translatable':"",
            'regex': '^ip\spim',
            'meraki': {
                'skip': True
            },
            'iosxe': "multicast_pim = parse.find_objects('^ip\spim')\n"
        },
        
        'static_routing':{
            'name': "Static routing",
            'support':"✓",
            'translatable':"",
            'regex': '^ip\sroute',
            'meraki': {
                'skip': True
            },
            'iosxe': "static_routing = parse.find_objects('^ip\sroute')\n"
        },
        
        'ipv6':{
            'name': "IPv6",
            'support':"✓",
            'translatable':"",
            'regex': '^ipv6',
            'meraki': {
                'skip': True
            },
            'iosxe': "ipv6 = parse.find_objects('^ipv6')\n"
        },
        
        'rip':{
            'name': "RIP",
            'support':"",
            'translatable':"",
            'regex': '^router rip',
            'meraki': {
                'skip': True
            },
            'iosxe': "rip = parse.find_objects('^router rip')\n",
            'url':"https://documentation.meraki.com/MS/Layer_3_Switching/MS_Layer_3_Switching_and_Routing",
            'note':"Not Supported"
        },
        
        'eigrp':{
            'name': "EIGRP",
            'support':"",
            'translatable':"",
            'regex': '^router eigrp',
            'meraki': {
                'skip': True
            },
            'iosxe': "eigrp = parse.find_objects('^router eigrp')\n",
            'url':"https://documentation.meraki.com/MS/Layer_3_Switching/MS_Layer_3_Switching_and_Routing",
            'note':"Not Supported"
        },
        
        'ospf':{
            'name': "OSPFv2",
            'support':"",
            'translatable':"",
            'regex': '^router ospf',
            'meraki': {
                'skip': True
            },
            'iosxe': "ospf = parse.find_objects('^router ospf')\n",
            'url':"https://documentation.meraki.com/MS/Layer_3_Switching/MS_Layer_3_Switching_and_Routing",
            'note':"Supported on MS250 and above"
        },
        
        'ospfv3':{
            'name': "OSPFv3",
            'support':"",
            'translatable':"",
            'regex': '^router ospfv3',
            'meraki': {
                'skip': True
            },
            'iosxe': "ospfv3 = parse.find_objects('^router ospfv3')\n",
            'url':"https://documentation.meraki.com/MS/Layer_3_Switching/MS_Layer_3_Switching_and_Routing",
            'note':"Not Supported"
        },
        
        'bgp':{
            'name': "BGP",
            'support':"",
            'translatable':"",
            'regex': '^router bgp',
            'meraki': {
                'skip': True
            },
            'iosxe': "bgp = parse.find_objects('^router bgp')\n",
            'url':"https://documentation.meraki.com/MX/Networks_and_Routing/Border_Gateway_Protocol_(BGP)",
            'note':"Currently supported on MX only"
        },
        
        'isis':{
            'name': "IS-IS",
            'support':"",
            'translatable':"",
            'regex': '^router isis',
            'meraki': {
                'skip': True
            },
            'iosxe': "isis = parse.find_objects('^router isis')\n",
            'url':"https://documentation.meraki.com/MS/Layer_3_Switching/MS_Layer_3_Switching_and_Routing",
            'note':"Not Supported"
        },
        
        'vrf': {
            'name': "VRF",
            'support':"",
            'translatable':"",
            'regex': '^vpms',
            'meraki': {
                'skip': True
            },
            'iosxe': "vrf = parse.find_objects('^vrf')\n",
            'url':"https://documentation.meraki.com/MS/Layer_3_Switching/MS_Layer_3_Switching_and_Routing",
            'note':"Not Supported"
        }
    },
    
    'port': {
        
        'name': {
            'name': "Port Description",
            'support':"✓",
            'translatable':"✓",
            'uplink':"✓",
            'downlink':"✓",
            'regex': r'\sdescription\s+(\S.+)',
            'meraki': {
                'skip': False,
                'default': ''
            },
            'iosxe': "name = child.re_match_typed(regex=r'\sdescription\s+(\S.+)')\n"
        },
        
        'speed': {
            'name': "Port Speed",
            'support':"✓",
            'translatable':"✓",
            'uplink':"✓",
            'downlink':"✓",
            'regex': r'\sspeed\s+(\S.*)',
            'meraki': {
                'skip': True,
                'default': ''
            },
            'iosxe': "speed = child.re_match_typed(regex=r'\sspeed\s+(\S.*)')\n"
        },
        
        'duplex': {
            'name': "Port Duplex",
            'support':"✓",
            'translatable':"✓",
            'uplink':"✓",
            'downlink':"✓",
            'regex': r'\sduplex\s+(\S.+)',
            'meraki': {
                'skip': True,
                'default': ''
            },
            'iosxe': "duplex = child.re_match_typed(regex=r'\sduplex\s+(\S.+)')\n",\
            
        },
        
        'linkNegotiation': {
            'uplink':"✓",
            'downlink':"✓",
            'iosxe': "",
            'regex': '',
            'meraki': {
                'skip': 'post-process',
                'default': 'Auto negotiate',
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
    linkNegotiation = 'Auto negotiate'\n"
            }
        },
        
        'type': {
            'name': "Port Type",
            'support':"✓",
            'translatable':"✓",
            'uplink':"✓",
            'downlink':"✓",
            'regex': r'\sswitchport\smode\s+(\S.+)',
            'meraki': {
                'skip': False,
                'default': 'trunk'
            },
            'iosxe': "type = child.re_match_typed(regex=r'\sswitchport\smode\s+(\S.+)')\n"
        },
        
        'poeEnabled': {
            'name': "Data VLAN",
            'support':"✓",
            'translatable':"✓",
            'uplink':"",
            'downlink':"✓",
            'regex': r'\spower\sinline\s+(\S.+)',
            'meraki': {
                'skip': False,
                'default': True
            },
            'iosxe': "poeEnabled = not child.re_match_typed(regex=r'\spower\sinline\s+(\S.+)')=='never'\n"
        },
        
        'allowedVlans': {
            'name': "Allowed VLANs",
            'support':"✓",
            'translatable':"✓",
            'uplink':"✓",
            'downlink':"✓",
            'regex': r'\sswitchport\strunk\sallowed\svlan\s+(\S.*)',
            'meraki': {
                'skip': False,
                'default': '1-1000'
            },
            'iosxe': "allowedVlans = child.re_match_typed(regex=r'\sswitchport\strunk\sallowed\svlan\s+(\S.*)')\n"
        },
        
        'vlan': {
            'name': "Data VLAN",
            'support':"✓",
            'translatable':"✓",
            'uplink':"✓",
            'downlink':"✓",
            'regex': r'\sswitchport\svlan\s+(\S.*)',
            'meraki': {
                'skip': False,
                'default': '1'
            },
            'iosxe': "vlan = child.re_match_typed(regex=r'\sswitchport\svlan\s+(\S.*)')\n"
        },
        
        'root_guard': {
            'iosxe': "root_guard = 'yes'\n",
            'regex': r'\sspanning-tree\sguard\sroot?(\S.*)',
            'meraki': {
                'skip': True,
                'default': ''
            }
        },
        
        'loop_guard': {
            'iosxe': "loop_guard = 'yes'\n",
            'regex': r'\sspanning-tree\sguard\sloop?(\S.*)',
            'meraki': {
                'skip': True,
                'default': ''
            }
        },
        
        'bpdu_guard': {
            'iosxe': "bpdu_guard =  'yes'\n",
            'regex': r'\sspanning-tree\sbpduguard?(\S.*)',
            'meraki': {
                'skip': True,
                'default': ''
            }
        },
        
        'stpGuard': {
            'iosxe': "",
            'regex': '',
            'meraki': {
                'skip': 'post-process',
                'post-process': "\
\
stpGuard = 'disabled'\n\
try:\n\
    if m['root_guard'] == 'yes':\n\
        stpGuard = 'root guard'\n\
except:\n\
    pass\n\
try:\n\
    if m['loop_guard'] == 'yes':\n\
        stpGuard = 'loop guard'\n\
except:\n\
    pass\n\
try:\n\
    if m['bpdu_guard'] == 'yes':\n\
        stpGuard = 'bpdu guard'\n\
except:\n\
    pass\n\
if debug:\n\
    print(f'stpGuard = {stpGuard}')\n",
                'default': 'disabled'
            }
        },
        
        'vlan': {
            'name': "Data VLAN",
            'support':"✓",
            'translatable':"✓",
            'uplink':"✓",
            'downlink':"✓",
            'regex': r'\sswitchport\strunk\snative\svlan\s+(\S.*)',
            'meraki': {
                'skip': False,
                'default': '1'
            },
            'iosxe': "vlan = child.re_match_typed(regex=r'\sswitchport\strunk\snative\svlan\s+(\S.*)')\n"
        },
        
        'voiceVlan': {
            'name': "Voice VLAN",
            'support':"✓",
            'translatable':"✓",
            'uplink':"✓",
            'downlink':"✓",
            'regex': r'\sswitchport\svoice\svlan\s+(\S.*)',
            'meraki': {
                'skip': False,
                'default': None
            },
            'iosxe': "voiceVlan = child.re_match_typed(regex=r'\sswitchport\svoice\svlan\s+(\S.*)')\n"
        },
        
        'private_vlan': {
            'name': "Private VLAN",
            'regex': r'\sswitchport\smode\sprivate-vlan?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "private_vlan = child.re_match_typed(regex=r'\sswitchport\smode\sprivate-vlan?(\S.*)')\n",
            'url':"https://documentation.meraki.com/MS/Port_and_VLAN_Configuration/Restricting_Traffic_with_Isolated_Switch_Ports",
            'note':"Port Isolation can be used"
        },
        
        'pruning': {
            'name': "Pruning",
            'support':"",
            'translatable':"",
            'regex': r'\sswitchport\strunk\spruning?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "pruning = child.re_match_typed(regex=r'\sswitchport\strunk\spruning?(\S.*)')\n",
            'url':"https://documentation.meraki.com/General_Administration/Tools_and_Troubleshooting/Fundamentals_of_802.1Q_VLAN_Tagging",
            'note':"Not required"
        },
        
        'stp_port': {
            'name': "STP Port Priority",
            'support':"",
            'translatable':"",
            'regex': r'\sspanning-tree\sport-priority?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "stp_port = child.re_match_typed(regex=r'\sspanning-tree\sport-priority?(\S.*)')\n"
        },
        
        'portfast': {
            'name': "STP Portfast",
            'support':"",
            'translatable':"",
            'regex': r'\sspanning-tree\sportfast?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "portfast = child.re_match_typed(regex=r'\sspanning-tree\sportfast?(\S.*)')\n"
        },
        
        'root_guard': {
            'name': "STP RootGuard",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sspanning-tree\sguard\sroot?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "root_guard = child.re_match_typed(regex=r'\sspanning-tree\sguard\sroot?(\S.*)')\n"
        },
        
        'loop_guard': {
            'name': "STP Loop Guard",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sspanning-tree\sguard\sloop?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "loop_guard = child.re_match_typed(regex=r'\sspanning-tree\sguard\sloop?(\S.*)')\n"
        },
        
        'bpdu_guard': {
            'name': "STP BPDU Guard",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sspanning-tree\sbpduguard?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "bpdu_guard = child.re_match_typed(regex=r'\sspanning-tree\sbpduguard?(\S.*)')\n"
        },
        
        'flex_links': {
            'name': "Flex Links",
            'support':"",
            'translatable':"",
            'regex': r'\sswitchport\sbackup\sinterface?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "flex_links = child.re_match_typed(regex=r'\sswitchport\sbackup\sinterface?(\S.*)')\n"
        },
        
        'storm_control': {
            'name': "Storm Control",
            'support':"",
            'translatable':"",
            'regex': r'\sstorm-control?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "storm_control = child.re_match_typed(regex=r'\sstorm-control?(\S.*)')\n",
            'url':"https://documentation.meraki.com/MS/Other_Topics/Storm_Control_for_MS",
            'note':"Network-wide"
        },
        
        'protected': {
            'name': "Protected",
            'support':"",
            'translatable':"",
            'regex': r'\sswitchport\sprotected?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "protected = child.re_match_typed(regex=r'\sswitchport\sprotected?(\S.*)')\n"
        },
        
        'port_security': {
            'name': "Port Security",
            'support':"✓",
            'translatable':"",
            'regex': r'\sswitchport\sport-security?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "port_security = child.re_match_typed(regex=r'\sswitchport\sport-security?(\S.*)')\n"
        },
        
        'port_udld': {
            'name': "Port UDLD",
            'support':"✓",
            'translatable':"",
            'regex': r'\sudld\sport?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "port_udld = child.re_match_typed(regex=r'\sudld\sport?(\S.*)')\n"
        },
        
        'lldp': {
            'name': "LLDP",
            'support':"",
            'translatable':"",
            'regex': r'\slldp?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "lldp = child.re_match_typed(regex=r'\slldp?(\S.*)')\n",
            'url':"https://documentation.meraki.com/General_Administration/Other_Topics/LLDP_Support_on_Cisco_Meraki_Products#ms",
            'note':"Always on"
        },
        
        'ipv6': {
            'name': "IPv6",
            'support':"",
            'translatable':"",
            'regex': r'\sipv6?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "ipv6 = child.re_match_typed(regex=r'\sipv6?(\S.*)')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported"
        },

        'directed_broadcast': {
            'name': "IP Directed Broadcast",
            'support':"",
            'translatable':"",
            'regex': r'\sip\sdirected-broadcast?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "directed_broadcast = child.re_match_typed(regex=r'\sip\sdirected-broadcast?(\S.*)')\n"
            },
        
        'etherchannel': {
            'name': "Etherchannel",
            'support':"",
            'translatable':"",
            'regex': r'^\schannel-group\s\d\smode\s+(\S.+)',
            'meraki': {
                'skip': True
            },
            'iosxe': "etherchannel = child.re_match_typed('^\schannel-group\s\d\smode\s+(\S.+)')\n",
            'url':"https://documentation.meraki.com/General_Administration/Tools_and_Troubleshooting/Link_Aggregation_and_Load_Balancing",
            'note':"Only LACP is supported"
        }
    }
}

def index_mc_pedia(index_args):
    blurb = "\n\n\
==============================\n\
      Index of mc_pedia\n"
    
    if len(index_args) == 0:
        blurb+="     All Reportable Items\n"        
    elif "support" in index_args:
        if "translatable" in index_args:
            blurb+="Supported & Translatable Items\n"
        else:
            blurb+="       Supported Items\n"
    elif "translatable" in index_args:
        blurb+="     Translatable Items\n"
    print(blurb+"==============================\n")
    for key,value in mc_pedia.items():
        print(key+":\n")
        for k,v in value.items():
            skip = 0
            if "translatable" in index_args:
                if "translatable" not in v:
                    skip = 1
                elif not v['translatable'] == "✓":
                    skip = 1
            if "support" in index_args:
                if "support" not in v:
                    skip = 1
                elif not v['support'] == "✓":
                    skip = 1
            if skip == 0:
                print(" - "+k+"\n")
    if len(index_args) == 0:
        print("\n\nTo print the index based on either supported and translatable items or both, enter")
        print("    python mc_pedia [support] [translatable]")

if __name__ == '__main__':
    index_args = list()
    if len(sys.argv) > 1:
        args = sys.argv
        del args[0]
        for arg in args:
            if arg.lower() == "support" or arg.lower() == "supportable":
                index_args.append("support")
            if arg.lower() == "translate" or arg.lower() == "translatable":
                index_args.append("translatable")
    index_mc_pedia(index_args)
