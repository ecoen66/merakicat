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
'skip', 'default' and OPTIONALLY 'post_process'.

The 'skip' value indicates whether or not to add this element to the meraki config,
or to do some post_processing for the meraki config.
    Examples include 'speed' & 'duplex', which have no direct
    relation to meraki config elements.

The 'default' value indicates the value to set for this port if there was no match
in the IOSXE config for the port.

The OPTIONAL 'post_process' value is the python code (as a string) to execute to
provide a generated value for the element in the meraki config loop.
    An example would be 'linkNegotiation' which must be
    determined based on a combination of 'speed' & 'duplex'.

#####################################################################################
'''


mc_pedia = {

    'version': "v0.1.5",
    'dated': "03/28/2024",

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
                'skip': 'post_process',
                'default': 'Auto negotiate',
                'post_process': "\
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
        r = dashboard.switch.getNetworkSwitchStacks(networkId=networkId)\n\
        for stack in r:\n\
            for serial in sw_list:\n\
                if serial in stack['serials'][0]:\n\
                    response = dashboard.switch.deleteNetworkSwitchStack(networkId,stack['id'])\n\
                    break\n\
        switchStackId = dashboard.switch.createNetworkSwitchStack(networkId=networkId, serials=sw_list, name=switch_name)['id']\n\
        if debug:\n\
            print(f'switchStackId = {switchStackId}')\n\
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
return_vals = ['urls','networkId','switchStackId']\n\
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
            'support':"✓",
            'translatable':"",
            'regex': '^mls',
            'meraki': {
                'skip': True
            },
            'iosxe': "mls = parse.find_objects('^mls')\n",
            'url':"https://documentation.meraki.com/MS/Other_Topics/MS_Switch_Quality_of_Service_Defined",
            'note':"Network-wide"
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
            'iosxe':"snmp = parse.find_objects('^snmp')\n",
            'url': "https://documentation.meraki.com/General_Administration/Monitoring_and_Reporting/SNMP_Overview_and_Configuration",
            'note': "Configured network-wide"
        },
        
        'logging_host':{
            'name': "Syslog",
            'support':"",
            'translatable':"",
            'regex': '^logging',
            'meraki': {
                'skip': True
            },
            'iosxe':"logging_host = parse.find_objects('^logging')\n",
            'url': "https://documentation.meraki.com/General_Administration/Monitoring_and_Reporting/Syslog_Server_Overview_and_Configuration",
            'note': "Configured network-wide"
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
            'iosxe': "access_list = parse.find_objects('^access-list')\n",
            'url':"https://documentation.meraki.com/MS/Access_Control/Meraki_MS_Group_Policy_Access_Control_Lists",
            'note':"Group Policies"
        },
        
        'extended_access_list':{
            'name': "Extended ACL",
            'support':"",
            'translatable':"",
            'regex': '^ip\saccess-list',
            'meraki': {
                'skip': True
            },
            'iosxe': "extended_access_list = parse.find_objects('^ip\saccess-list')\n",
            'url':"https://documentation.meraki.com/MS/Access_Control/Meraki_MS_Group_Policy_Access_Control_Lists",
            'note':"Group Policies"
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
        
        'dot1x':{
            'name': "802.1x",
            'support': "✓",
            'translatable':"",
            'regex': '^aaa authentication dot1x',
            'meraki': {
                'skip': True
            },
            'iosxe': "dot1x = parse.find_objects('^aaa authentication dot1x')\n",
            'url':"https://documentation.meraki.com/MS/Access_Control/MS_Switch_Access_Policies_(802.1X)",
            'note':"Network-wide"
        },
        
        'netflow':{
            'name': "NetFlow",
            'support':"✓",
            'translatable':"",
            'regex': '^flow\sexporter',
            'meraki': {
                'skip': True
            },
            'iosxe': "netflow = parse.find_objects('^flow\sexporter')\n",
            'url':"https://documentation.meraki.com/MS/Monitoring_and_Reporting/MS_NetFlow_and_Encrypted_Traffic_Analytics",
            'note':"Network-wide"
        },
        
        'dhcp':{
            'name':"DHCP server",
            'support':"✓",
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
            'name':"Radius",
            'support':"✓",
            'translatable':"",
            'regex': '^radius-server|^radius\sserver',
            'meraki': {
                'skip': True
            },
            'iosxe':"radius = parse.find_objects('^radius-server|^radius\sserver')\n"
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
            'note':"Not required"
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
        
        'vmps':{
            'name': "VMPS",
            'support':"",
            'translatable':"",
            'regex': '^vpms',
            'meraki': {
                'skip': True
            },
            'iosxe': "vmps = parse.find_objects('^vmps')\n",
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
            'support':"✓",
            'translatable':"",
            'regex': '^ip\sdhcp\ssnooping',
            'meraki': {
                'skip': True
            },
            'iosxe': "dhcp_snooping = parse.find_objects('ip\sdhcp\ssnooping')\n",
            'url':"https://documentation.meraki.com/MS/Other_Topics/Dynamic_ARP_Inspection",
            'note':"Network-wide"
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
            'support':"✓",
            'translatable':"",
            'regex': '^ip\sarp\sinspection',
            'meraki': {
                'skip': True
            },
            'iosxe': "arp_inspection = parse.find_objects('^ip\sarp\sinspection')\n",
            'url':"https://documentation.meraki.com/MS/Other_Topics/Dynamic_ARP_Inspection",
            'note':"Network-wide"
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
            'iosxe': "logging = parse.find_objects('^logging')\n",
            'url': "https://documentation.meraki.com/General_Administration/Cross-Platform_Content/Meraki_Event_Log",
            'note':"Configured by default"
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
            'iosxe': "multicast_igmp = parse.find_objects('^ip\sigmp')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Configured by default"
        },
        
        'multicast_pim':{
            'name': "Multicast PIM",
            'support':"✓",
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
            'translatable':"✓",
            'regex': '^ip\sroute',
            'iosxe': "\
static_routing = list()\n\
route_obj_list = parse.find_objects('^ip\sroute\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')\n\
for route_obj in route_obj_list:\n\
    net = route_obj.re_match_typed('^ip\sroute\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')\n\
    mask = route_obj.re_match_typed('^ip\sroute\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')\n\
    gw = route_obj.re_match_typed('^ip\sroute\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')\n\
    import ipaddress\n\
    subnet = str(ipaddress.ip_network(net + '/' + mask, strict=False))\n\
    static_routing.append({'net': net, 'mask': mask, 'gw': gw, 'subnet': subnet})\n",
            'meraki': {
                'skip': 'post_ports',
                'post_process': "\
for route in switch_dict['static_routing']:\n\
    if route['subnet'] == '0.0.0.0/0':\n\
        default_route = route\n\
        return_vals = ['default_route']\n",
                'post_ports_process': "\
for route in switch_dict['static_routing']:\n\
    if not route['subnet'] == '0.0.0.0/0':\n\
        if 'switchStackId' in switch_dict.keys():\n\
            dashboard.switch.createNetworkSwitchStackRoutingStaticRoute(switch_dict['networkId'],switch_dict['switchStackId'],route['subnet'],route['gw'])\n\
        else:\n\
            if len(sw_list) == 1:\n\
                dashboard.switch.createDeviceSwitchRoutingStaticRoute(swlist[0],route['subnet'],route['gw'])\n"
            }
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
            'support':"✓",
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
            'regex': r'\sdescription\s+(\S.+)',
            'meraki': {
                'skip': False,
                'default': ''
            },
            'iosxe': "name = child.re_match_typed(regex=r'\sdescription\s+(\S.+)')\n"
        },
        
        'active': {
            'name': "Port Status",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\s(shutdown)',
            'meraki': {
                'skip': False,
                'default': 'true'
            },
            'iosxe': "\
shut = child.re_match_typed(regex=r'\s(shutdown)')\n\
active = 'true' if shut == '' else 'false'\n"
        },
        
        'speed': {
            'name': "Port Speed",
            'support':"✓",
            'translatable':"✓",
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
            'regex': r'\sduplex\s+(\S.+)',
            'meraki': {
                'skip': True,
                'default': ''
            },
            'iosxe': "duplex = child.re_match_typed(regex=r'\sduplex\s+(\S.+)')\n",\
            
        },
        
        'linkNegotiation': {
            'iosxe': "",
            'regex': '',
            'meraki': {
                'skip': 'post_process',
                'default': 'Auto negotiate',
                'post_process': "\
\
linkNegotiation = ''\n\
try:\n\
    speed = int(intf_settings['speed'])\n\
    if speed < 1000:\n\
        linkNegotiation += str(speed)+' Megabit '\n\
    else:\n\
        linkNegotiation += str(int(speed/1000))+' Gigabit '\n\
    try:\n\
        duplex = intf_settings['duplex']\n\
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
            'regex': r'\sswitchport\smode\s+(\S.+)',
            'meraki': {
                'skip': False,
                'default': 'trunk'
            },
            'iosxe': "type = child.re_match_typed(regex=r'\sswitchport\smode\s+(\S.+)')\n"
        },
        
        'poeEnabled': {
            'name': "PoE Enabled",
            'support':"✓",
            'translatable':"✓",
            'uplink':"",
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
            'regex': r'\sswitchport\strunk\sallowed\svlan\s+(\S.*)',
            'meraki': {
                'skip': False,
                'default': '1-1000'
            },
            'iosxe': "allowedVlans = child.re_match_typed(regex=r'\sswitchport\strunk\sallowed\svlan\s+(\S.*)')\n"
        },
        
        'vlan': {
            'name': "Native VLAN",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sswitchport\strunk\snative\svlan\s+(\S.*)',
            'meraki': {
                'skip': False,
                'default': '1'
            },
            'iosxe': "vlan = child.re_match_typed(regex=r'\sswitchport\strunk\snative\svlan\s+(\S.*)')\n"
        },
        
        'vlan': {
            'name': "Data VLAN",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sswitchport\svlan\s+(\S.*)',
            'meraki': {
                'skip': False,
                'default': '1'
            },
            'iosxe': "vlan = child.re_match_typed(regex=r'\sswitchport\svlan\s+(\S.*)')\n"
        },
        
        'voiceVlan': {
            'name': "Voice VLAN",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sswitchport\svoice\svlan\s+(\S.*)',
            'meraki': {
                'skip': False,
                'default': None
            },
            'iosxe': "voiceVlan = child.re_match_typed(regex=r'\sswitchport\svoice\svlan\s+(\S.*)')\n"
        },
        
        'private_vlan': {
            'name': "Private VLAN",
            'support':"",
            'translatable':"",
            'regex': r'\sswitchport\smode\sprivate-vlan?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "private_vlan = child.re_match_typed(regex=r'\sswitchport\smode\sprivate-vlan?(\S.*)')\n",
            'url':"https://documentation.meraki.com/MS/Port_and_VLAN_Configuration/Restricting_Traffic_with_Isolated_Switch_Ports",
            'note':"Port Isolation can be used"
        },
        
        'l3_interface': {
            'name': "Layer 3 Interface",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sip\saddress\s(\S.*)',
            'meraki': {
                'skip': 'post_ports',
                'post_process':"l3_interface = True\n\
return_vals=['l3_interface']\n",
                'post_ports_process': "\
conf_ports = list()\n\
unconf_ports = list()\n\
l3_ports = [v for k, v in port_dict.items() if 'Vlan' in k]\n\
if debug:\n\
    print(f'l3_ports = {l3_ports}')\n\
x = 0\n\
while x < len(l3_ports):\n\
    if debug:\n\
        print(f'l3_ports[{x}] = {l3_ports[x]}')\n\
        print(f'l3_ports[{x}][meraki_args] = ')\n\
        print(l3_ports[x]['meraki_args'])\n\
    ma = l3_ports[x]['meraki_args']\n\
    if 'defaultGateway' in ma[4].keys():\n\
        try:\n\
            if 'switchStackId' in switch_dict.keys():\n\
                dashboard.switch.createNetworkSwitchStackRoutingInterface(ma[0],ma[1],ma[2],ma[3],**ma[4])\n\
            else:\n\
                dashboard.switch.createDeviceSwitchRoutingInterface(swlist[0],name=ma[2],vlanId=ma[3],**ma[4])\n\
            conf_ports.append(ma[2])\n\
        except:\n\
            print(f'We had an issue creating {ma[2]}.')\n\
            unconf_ports.append(ma[2])\n\
        dg = x\n\
        break\n\
    x+=1\n\
x = 0\n\
while x < len(l3_ports):\n\
    if not x == dg:\n\
        ma = l3_ports[x]['meraki_args']\n\
        try:\n\
            if 'switchStackId' in switch_dict.keys():\n\
                dashboard.switch.createNetworkSwitchStackRoutingInterface(ma[0],ma[1],ma[2],ma[3],**ma[4])\n\
            else:\n\
                dashboard.switch.createDeviceSwitchRoutingInterface(swlist[0],name=ma[2],vlanId=ma[3],**ma[4])\n\
            conf_ports.append(ma[2])\n\
        except:\n\
            print(f'We had an issue creating {ma[2]}.')\n\
            unconf_ports.append(ma[2])\n\
    x+=1\n\
return_vals = ['l3_ports','conf_ports','unconf_ports']\n"
            },
            'iosxe': "l3_interface = child.re_match_typed(regex=r'\sip\saddress\s(\S.*)')\n"
        },
        
        'root_guard': {
            'name': "STP Root Guard",
            'support':"✓",
            'translatable':"✓",
            'iosxe': "root_guard = 'yes'\n",
            'regex': r'\sspanning-tree\sguard\sroot?(\S.+)',
            'meraki': {
                'skip': True,
                'default': ''
            }
        },
        
        'loop_guard': {
            'name': "STP Loop Guard",
            'support':"✓",
            'translatable':"✓",
            'iosxe': "loop_guard = 'yes'\n",
            'regex': r'\sspanning-tree\sguard\sloop?(\S.+)',
            'meraki': {
                'skip': True,
                'default': ''
            }
        },
        
        'bpdu_guard': {
            'name': "STP BPDU Guard",
            'support':"✓",
            'translatable':"✓",
            'iosxe': "bpdu_guard =  'yes'\n",
            'regex': r'\sspanning-tree\sbpduguard?(\S.+)',
            'meraki': {
                'skip': True,
                'default': ''
            }
        },
        
        'stpGuard': {
            'iosxe': "",
            'regex': '',
            'meraki': {
                'skip': 'post_process',
                'post_process': "\
\
stpGuard = 'disabled'\n\
try:\n\
    if intf_settings['root_guard'] == 'yes':\n\
        stpGuard = 'root guard'\n\
except:\n\
    pass\n\
try:\n\
    if intf_settings['loop_guard'] == 'yes':\n\
        stpGuard = 'loop guard'\n\
except:\n\
    pass\n\
try:\n\
    if intf_settings['bpdu_guard'] == 'yes':\n\
        stpGuard = 'bpdu guard'\n\
except:\n\
    pass\n\
if debug:\n\
    print(f'stpGuard = {stpGuard}')\n",
                'default': 'disabled'
            }
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
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sspanning-tree\sportfast?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "portfast = child.re_match_typed(regex=r'\sspanning-tree\sportfast?(\S.*)')\n",
            'url':"https://documentation.meraki.com/MS/Deployment_Guides/Advanced_MS_Setup_Guide",
            'note':"Automatic Edge Port"
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
            'note':"Configured network-wide"
        },
        
        'protected': {
            'name': "Protected",
            'support':"✓",
            'translatable':"",
            'regex': r'\sswitchport\sprotected?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "protected = child.re_match_typed(regex=r'\sswitchport\sprotected?(\S.*)')\n",
            'url':"https://documentation.meraki.com/MS/Port_and_VLAN_Configuration/Restricting_Traffic_with_Isolated_Switch_Ports",
            'note':"Port Isolation"
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
        
        'etherchannel_cisco': {
            'name': "Etherchannel Classic",
            'support':"",
            'translatable':"",
            'regex': r'^\schannel-group\s\d+\smode\s(on)',
            'meraki': {
                'skip': True
            },
            'iosxe': "etherchannel_cisco = 'on'\n",
            'url':"https://documentation.meraki.com/General_Administration/Tools_and_Troubleshooting/Link_Aggregation_and_Load_Balancing",
            'note':"Only LACP is supported"
        },
        
        'etherchannel_pagp': {
            'name': "Etherchannel PAgP",
            'support':"",
            'translatable':"",
            'regex': r'^\schannel-group\s\d+\smode\s(auto|desirable)',
            'meraki': {
                'skip': True
            },
            'iosxe': "etherchannel_pagp = child.re_match_typed('^\schannel-group\s\d+\smode\s(auto|desirable)')\n",
            'url':"https://documentation.meraki.com/General_Administration/Tools_and_Troubleshooting/Link_Aggregation_and_Load_Balancing",
            'note':"Only LACP is supported"
        },
        
        'etherchannel_lacp': {
            'name': "Etherchannel LACP",
            'support':"✓",
            'translatable':"✓",
            'regex': r'^\schannel-group\s\d+\smode\s(active|passive)',
            'meraki': {
                'skip': True
            },
            'iosxe': "etherchannel_lacp = child.re_match_typed('^\schannel-group\s(\d+)')\n"
        },
        
        'etherchannel': {
            'iosxe': "",
            'regex': '',
            'meraki': {
                'skip': 'post_ports',
                'post_process': "\
if 'etherchannel_lacp' in intf_settings:\n\
    if debug:\n\
        print('etherchannel_lacp = ' + intf_settings['etherchannel_lacp'])\n\
    group = intf_settings['etherchannel_lacp']\n\
    serial = sw_list[switch_num]\n\
    portId = intf_settings['port']\n\
    if debug:\n\
        print('group = ' + group + ', switch_num = ' + str(switch_num) + ', serial = ' + serial + ', portId = ' + portId)\n\
    etherchannel = {'group': group, 'switch_num': switch_num, 'serial': serial, 'portId': portId}\n\
    if debug:\n\
        print(etherchannel)\n\
    return_vals = ['etherchannel']\n\
    if debug:\n\
        print(return_vals)\n",
            'post_ports_process': "\
if debug:\n\
    print(f'In post_ports_process, post_ports_list = {post_ports_list}')\n\
    print(f'Length of post_ports_list is {len(post_ports_list)}')\n\
# Get a list of array positions where 'etherchannel' appears in our post_ports_list \n\
channel_positions = [i for i in range(len(post_ports_list)) if post_ports_list[i][0] == 'etherchannel']\n\
if debug:\n\
    print(f'channel_positions = {channel_positions}')\n\
# Create a dictionary of lists to hold the data needed to create each etherchannel \n\
channel_dict = dict(list())\n\
channel_port_dict = {}\n\
#action_list = list()\n\
x = 0\n\
# Loop through the relevant positions in the post_ports_list, and append the required data \n\
# to the dictionary of lists that holds the data for each etherchannel \n\
while x < len(channel_positions):\n\
    if debug:\n\
        print(f'post_ports_list[channel_positions[x]][1] = {post_ports_list[channel_positions[x]][1]}')\n\
    group = post_ports_list[channel_positions[x]][1]['group']\n\
    # We need to remove 'group' from the dictionary of values now before adding the \n\
    # other dictionary entries to the list that Dashboard will process for this \n\
    # etherchannel group \n\
    post_ports_list[channel_positions[x]][1].pop('group')\n\
    post_ports_list[channel_positions[x]][1].pop('switch_num')\n\
    if debug:\n\
        print(f'group = {group}')\n\
    if group not in channel_dict.keys():\n\
        channel_dict[group] = []\n\
    # Append the 'serial' and 'port' key, value pairs to the switchPorts list for this \n\
    # etherchannel group \n\
    channel_dict[group].extend([post_ports_list[channel_positions[x]][1]])\n\
    if debug:\n\
        print(f'In loop x = {x}, channel_dict = {channel_dict}')\n\
    x+=1\n\
if debug:\n\
    print(f'channel_dict = {channel_dict}')\n\
return_vals = list()\n\
if debug:\n\
    print(f'len(channel_dict) = {len(channel_dict)}')\n\
key_list =list(channel_dict.keys())\n\
x = 0\n\
while x < len(key_list):\n\
    if debug:\n\
        print(f'key = {key_list[x]}, channel_dict[{key_list[x]}] = {channel_dict[key_list[x]]}')\n\
        print(f'switchPorts = {channel_dict[key_list[x]]}')\n\
        print('networkId = ' + returns_dict['networkId'])\n\
    interface_descriptor = 'Port-channel' + key_list[x]\n\
    channel_port_dict[interface_descriptor] = port_dict[interface_descriptor]\n\
    channel_port_dict[interface_descriptor]['meraki_args'] = [returns_dict['networkId'],channel_dict[key_list[x]]]\n\
    try:\n\
        #action_list.append(dashboard.switch.createNetworkSwitchLinkAggregation(returns_dict['networkId'], switchPorts = channel_dict[key]))\n\
        r = dashboard.switch.createNetworkSwitchLinkAggregation(returns_dict['networkId'], switchPorts = channel_dict[key_list[x]])\n\
        if debug:\n\
            print(f'channel_port_dict = {channel_port_dict}')\n\
        channel_port_dict[interface_descriptor]['id'] = r['id']\n\
        if debug:\n\
            print(f'channel_port_dict[{interface_descriptor}] = {channel_port_dict[interface_descriptor]}')\n\
            print(f'Dashboard response was {r}')\n\
    except:\n\
        print(f'Exception in port-channel')\n\
        continue\n\
    x+=1\n\
return_vals = ['channel_port_dict']\n"
            }
        }
    },
    'layer3': {
        
        'interfaceIp': {
            'iosxe': "",
            'regex': '',
            'meraki': {
                'skip': 'post_process',
                'post_process': "\
interfaceIp = ''\n\
if 'l3_interface' in intf_settings.keys():\n\
    import re\n\
    if not intf_settings['l3_interface'] == '':\n\
        interfaceIp = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', intf_settings['l3_interface'])[0]\n"
            }
        },
        
        'subnet': {
            'iosxe': "",
            'regex': '',
            'meraki': {
                'skip': 'post_process',
                'post_process': "\
if 'l3_interface' in intf_settings.keys():\n\
        import re\n\
        subnet = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', intf_settings['l3_interface'])[0]\n\
        import ipaddress\n\
        if debug:\n\
            print(f'intf_settings = {intf_settings}')\n\
        subnet = str(ipaddress.ip_network(intf_settings['interfaceIp'] + '/' + subnet, strict=False))\n\
        defaultGateway = switch_dict['default_route']['gw']\n\
        if ipaddress.ip_address(defaultGateway) in ipaddress.ip_network(subnet):\n\
            if debug:\n\
                print(f'defaultGateway = {defaultGateway}')\n\
            return_vals = ['defaultGateway']\n"
            }
        }
    }
}

nm_dict = {
    "2x40G":
  {
    "supported": True,
    "ports": [
    r'FortyGigabitEthernet\d/1/1',
    r'FortyGigabitEthernet\d/1/2'
    ],
    "description": ""
  },
    "4x10G":
  {
    "supported": True,
    "ports": [
    r'GigabitEthernet\d/1/1',
    r'GigabitEthernet\d/1/2',
    r'GigabitEthernet\d/1/3',
    r'GigabitEthernet\d/1/4',
    r'TenGigabitEthernet\d/1/1',
    r'TenGigabitEthernet\d/1/2',
    r'TenGigabitEthernet\d/1/3',
    r'TenGigabitEthernet\d/1/4'
    ],
    "description": ""
  },
    "8x10G":
  {
    "supported": True,
    "ports": [
    r'GigabitEthernet\d/1/1',
    r'GigabitEthernet\d/1/2',
    r'GigabitEthernet\d/1/3',
    r'GigabitEthernet\d/1/4',
    r'GigabitEthernet\d/1/5',
    r'GigabitEthernet\d/1/6',
    r'GigabitEthernet\d/1/7',
    r'GigabitEthernet\d/1/8',
    r'TenGigabitEthernet\d/1/1',
    r'TenGigabitEthernet\d/1/2',
    r'TenGigabitEthernet\d/1/3',
    r'TenGigabitEthernet\d/1/4',
    r'TenGigabitEthernet\d/1/5',
    r'TenGigabitEthernet\d/1/6',
    r'TenGigabitEthernet\d/1/7',
    r'TenGigabitEthernet\d/1/8'
    ],
    "description": ""
  },
    "C3850-NM-2-10G":
  {
    "supported": False,
    "ports": [
    r'GigabitEthernet\d/1/1',
    r'GigabitEthernet\d/1/2',
    r'GigabitEthernet\d/1/3',
    r'GigabitEthernet\d/1/4',
    r'TenGigabitEthernet\d/1/3',
    r'TenGigabitEthernet\d/1/4'
    ],
    "description": "Catalyst 3850 4 x Gigabit Ethernet/2 x 10 Gigabit Ethernet Network Module"
  },
    "C3850-NM-2-40G":
  {
    "supported": True,
    "ports": [
    r'FortyGigabitEthernet\d/1/1',
    r'FortyGigabitEthernet\d/1/2'
    ],
    "description": "Catalyst 3850 2 x 40 Gigabit Ethernet Network Module"
  },
    "C3850-NM-4-1G":
  {
    "supported": True,
    "ports": [
    r'GigabitEthernet\d/1/1',
    r'GigabitEthernet\d/1/2',
    r'GigabitEthernet\d/1/3',
    r'GigabitEthernet\d/1/4'
    ],
    "description": "Catalyst 3850 4 x Gigabit Ethernet Network Module"
  },
    "C3850-NM-4-10G":
  {
    "supported": True,
    "ports": [
    r'GigabitEthernet\d/1/1',
    r'GigabitEthernet\d/1/2',
    r'GigabitEthernet\d/1/3',
    r'GigabitEthernet\d/1/4',
    r'TenGigabitEthernet\d/1/1',
    r'TenGigabitEthernet\d/1/2',
    r'TenGigabitEthernet\d/1/3',
    r'TenGigabitEthernet\d/1/4'
    ],
    "description": "Catalyst 3850 4 x Gigabit Ethernet/4 x 10 Gigabit Ethernet Network Module"
  },
    "C3850-NM-8-10G":
  {
    "supported": True,
    "ports": [
    r'GigabitEthernet\d/1/1',
    r'GigabitEthernet\d/1/2',
    r'GigabitEthernet\d/1/3',
    r'GigabitEthernet\d/1/4',
    r'GigabitEthernet\d/1/5',
    r'GigabitEthernet\d/1/6',
    r'GigabitEthernet\d/1/7',
    r'GigabitEthernet\d/1/8',
    r'TenGigabitEthernet\d/1/1',
    r'TenGigabitEthernet\d/1/2',
    r'TenGigabitEthernet\d/1/3',
    r'TenGigabitEthernet\d/1/4',
    r'TenGigabitEthernet\d/1/5',
    r'TenGigabitEthernet\d/1/6',
    r'TenGigabitEthernet\d/1/7',
    r'TenGigabitEthernet\d/1/8'
    ],
    "description": "Catalyst 3850 8 x Gigabit Ethernet/8 x 10 Gigabit Ethernet Network Module"
  },
    "C9300-NM-2C":
  {
    "supported": True,
    "ports": [
    r'FortyGigabitEthernet\d/1/1',
    r'FortyGigabitEthernet\d/1/2',
    r'HundredGigabitEthernet\d/1/1',
    r'HundredGigabitEthernet\d/1/2'
    ],
    "description": "Catalyst 9300 2 x 100G/40G dual rate QSFP Network Module"
  },
    "C9300-NM-2Q":
  {
    "supported": True,
    "ports": [
    r'FortyGigabitEthernet\d/1/1',
    r'FortyGigabitEthernet\d/1/2'
    ],
    "description": "Catalyst 9300 2 x 40GE QSFP Network Module"
  },
    "C9300-NM-2Y":
  {
    "supported": True,
    "ports": [
    r'GigabitEthernet\d/1/1',
    r'GigabitEthernet\d/1/2',
    r'TenGigabitEthernet\d/1/1',
    r'TenGigabitEthernet\d/1/2',
    r'TenGigabitEthernet\d/1/3',
    r'TwentyFiveGigE\d/1/1',
    r'TwentyFiveGigE\d/1/2'
    ],
    "description": "Catalyst 9300 2 x 25G/10G/1G SFP28 Network Module"
  },
    "C9300-NM-4C":
  {
    "supported": True,
    "ports": [
    r'FortyGigabitEthernet\d/1/1',
    r'FortyGigabitEthernet\d/1/2',
    r'FortyGigabitEthernet\d/1/3',
    r'FortyGigabitEthernet\d/1/4',
    r'HundredGigabitEthernet\d/1/1',
    r'HundredGigabitEthernet\d/1/2',
    r'HundredGigabitEthernet\d/1/3',
    r'HundredGigabitEthernet\d/1/4'
    ],
    "description": "Catalyst 9300 4 x 100G/40G dual rate QSFP Network Module"
  },
    "C9300-NM-4G":
  {
    "supported": True,
    "ports": [
    r'GigabitEthernet\d/1/1',
    r'GigabitEthernet\d/1/2',
    r'GigabitEthernet\d/1/3',
    r'GigabitEthernet\d/1/4'
    ],
    "description": "Catalyst 9300 4 x 1GE SFP Network Module"
  },
    "C9300-NM-4M":
  {
    "supported": True,
    "ports": [
    r'TenGigabitEthernet\d/1/1',
    r'TenGigabitEthernet\d/1/2',
    r'TenGigabitEthernet\d/1/3',
    r'TenGigabitEthernet\d/1/4'
    ],
    "description": "Catalyst 9300 4 x 10G/mGig copper Network Module"
  },
    "C9300-NM-8M":
  {
    "supported": True,
    "ports": [
    r'TenGigabitEthernet\d/1/1',
    r'TenGigabitEthernet\d/1/2',
    r'TenGigabitEthernet\d/1/3',
    r'TenGigabitEthernet\d/1/4',
    r'TenGigabitEthernet\d/1/5',
    r'TenGigabitEthernet\d/1/6',
    r'TenGigabitEthernet\d/1/7',
    r'TenGigabitEthernet\d/1/8'
    ],
    "description": "Catalyst 9300X 8 x 10G/mGig copper Network Module"
  },
    "C9300-NM-8X":
  {
    "supported": True,
    "ports": [
    r'GigabitEthernet\d/1/1',
    r'GigabitEthernet\d/1/2',
    r'GigabitEthernet\d/1/3',
    r'GigabitEthernet\d/1/4',
    r'GigabitEthernet\d/1/5',
    r'GigabitEthernet\d/1/6',
    r'GigabitEthernet\d/1/7',
    r'GigabitEthernet\d/1/8',
    r'TenGigabitEthernet\d/1/1',
    r'TenGigabitEthernet\d/1/2',
    r'TenGigabitEthernet\d/1/3',
    r'TenGigabitEthernet\d/1/4',
    r'TenGigabitEthernet\d/1/5',
    r'TenGigabitEthernet\d/1/6',
    r'TenGigabitEthernet\d/1/7',
    r'TenGigabitEthernet\d/1/8'
    ],
    "description": "Catalyst 9300 8 x 10G/1G SFP+ Network Module"
  },
    "C9300-NM-8Y":
  {
    "supported": True,
    "ports": [
    r'GigabitEthernet\d/1/1',
    r'GigabitEthernet\d/1/2',
    r'GigabitEthernet\d/1/3',
    r'GigabitEthernet\d/1/4',
    r'GigabitEthernet\d/1/5',
    r'GigabitEthernet\d/1/6',
    r'GigabitEthernet\d/1/7',
    r'GigabitEthernet\d/1/8',
    r'TenGigabitEthernet\d/1/1',
    r'TenGigabitEthernet\d/1/2',
    r'TenGigabitEthernet\d/1/3',
    r'TenGigabitEthernet\d/1/4',
    r'TenGigabitEthernet\d/1/5',
    r'TenGigabitEthernet\d/1/6',
    r'TenGigabitEthernet\d/1/7',
    r'TenGigabitEthernet\d/1/8',
    r'TwentyFiveGigE\d/1/1',
    r'TwentyFiveGigE\d/1/2',
    r'TwentyFiveGigE\d/1/3',
    r'TwentyFiveGigE\d/1/4',
    r'TwentyFiveGigE\d/1/5',
    r'TwentyFiveGigE\d/1/6',
    r'TwentyFiveGigE\d/1/7',
    r'TwentyFiveGigE\d/1/8'
    ],
    "description": "Catalyst 9300 8 x 25G/10G/1G multi-rate SFP Network Module"
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
        if key in ["version","dated"]:
            print(key+": "+value+"\n")
        else:
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
                    if "name" in v:
                        print(" - "+v['name']+"\n")
                    else:
                        print(" - "+k+" (for Meraki)\n")
    if len(index_args) == 0:
        print("\n\nTo print the index based on either supported and translatable items or both, enter")
        print("    python mc_pedia.py [support] [translatable]")

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
