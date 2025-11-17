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

    'version': "v1.0.0",
    'dated': "11/14/2025",

    'switch': {

        'switch_name': {
            'name': "Hostname",
            'support':"✓",
            'translatable':"✓",
            'regex': '^hostname',
            'iosxe': """
switch_name = ''
switch_name_obj = parse.find_objects('^hostname')
if not switch_name_obj == []:
    switch_name = switch_name_obj[0].re_match_typed('^hostname\s(\S+)',default='Switch')
if switch_name == '':
    switch_name = 'Switch'
host_name = switch_name
if debug:
    print(f'switch_name = {switch_name}')
""",

            'meraki': {
                'skip': 'post_process',
                'default': 'Auto negotiate',
                'post_process': """
urls = list()
blurb = 'This was a conversion from a Catalyst IOSXE config.'
n = 0
if debug:
    print(f'dir() = {dir()}')
switch_name = switch_dict['switch_name']
if switch_name == '':
    switch_name = 'Switch'
if len(sw_list) == 1:
    try:
        ## Set the switch name and notes
        response = dashboard.devices.updateDevice(sw_list[n], name=switch_name, notes=blurb)
        urls.append(response['url'])
        networkId = response['networkId']
        if debug:
            print(f'Dashboard response was: {response}')
    except:
        print(f'Unable to configure name on switch.')
    return_vals = ['urls','networkId']
else:
    while n <= len(sw_list)-1:
        try:
            ## Set the switch name and notes
            response = dashboard.devices.updateDevice(sw_list[n], name=switch_name+'-'+str(n+1), notes=blurb)
            urls.append(response['url'])
            networkId = response['networkId']
            if debug:
                print(f'Dashboard response was: {response}')
        except:
            print('Cannot set the switch name for switch ' + switch_name+'-'+str(n+1))
        n +=1
    if debug:
        print(f'networkId = {networkId}')
    try:
        ## Create the switch stack
        r = dashboard.switch.getNetworkSwitchStacks(networkId=networkId)
        for stack in r:
            for serial in sw_list:
                if serial in stack['serials'][0]:
                    response = dashboard.switch.deleteNetworkSwitchStack(networkId,stack['id'])
                    break
        switchStackId = dashboard.switch.createNetworkSwitchStack(networkId=networkId, serials=sw_list, name=switch_name)['id']
        if debug:
            print(f'switchStackId = {switchStackId}')
            print(f'Dashboard response to Create Stack was: {response}')
    # Oops, we got a Dashboard ERROR while claiming the switches to the network
    except Exception as e:
       if debug:
           print(f'Meraki API error: {e}')
           print(f'status code = {e.status}')
           print(f'reason = {e.reason}')
           print(f'error = {e.message}')
       if not e.message['errors'][0] == 'Cannot stack switches that are already part of a switch stack':
           print(f'Cannot create switch stack {switch_name} with {sw_list}.')
    return_vals = ['urls','networkId','switchStackId']
if debug:
    print(f'dir() = {dir()}')
"""
            }
        },

        'model':{
            'name': "Model",
            'support':"",
            'translatable':"",
            'regex': '^switch',
            'meraki': {
                'skip': True
            },
            'iosxe': """
model = []
stack_obj_list = parse.find_objects('^switch')
x = 1
while x <= len(stack_obj_list):
    model.append(stack_obj_list[0].re_match_typed('^switch\\s\\d{1}\\sprovision\\s(\\S+)'))
    x +=1
"""
        },

        'vtp':{
            'name': "VTP",
            'support':"",
            'translatable':"",
            'regex': '^vtp',
            'meraki': {
                'skip': True
            },
            'iosxe': "vtp = parse.find_objects('^vtp')",
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
            'iosxe': "mls = parse.find_objects('^mls')",
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
            'iosxe': "rstp = parse.find_objects('^spanning-tree mode rapid-pvst')"
        },

        'spanning':{
            'name':"Spanning Tree",
            'support':"",
            'translatable':"",
            'regex': '^spanning-tree',
            'meraki': {
                'skip': True
            },
            'iosxe': """
spanning = ''
if parse.find_objects('^spanning-tree extend system-id') == '':
    if parse.find_objects('^spanning-tree mode rapid-pvst') == '':
        spanning = parse.find_objects('^spanning-tree\s+(\S.+)')
""",
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
            'iosxe':"snmp = parse.find_objects('^snmp')",
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
            'iosxe':"logging_host = parse.find_objects('^logging')",
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
            'iosxe':"ntp = parse.find_objects('^ntp')",
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
            'iosxe': "access_list = parse.find_objects('^access-list')",
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
            'iosxe': "extended_access_list = parse.find_objects('^ip\saccess-list')",
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
            'iosxe': "port_mirror = parse.find_objects('^monitor')"
        },

        'aaa':{
            'name': "AAA",
            'support':"",
            'translatable':"",
            'regex': '^aaa',
            'meraki': {
                'skip': True
            },
            'iosxe': "aaa = parse.find_objects('^aaa')",
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
            'iosxe': "dot1x = parse.find_objects('^aaa authentication dot1x')",
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
            'iosxe': "netflow = parse.find_objects('^flow\sexporter')",
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
            'iosxe':"dhcp = parse.find_objects('^ip\sdhcp\spool')"
        },

        'banner':{
            'name': "Banner",
            'support':"",
            'translatable':"",
            'regex': '^banner',
            'meraki': {
                'skip': True
            },
            'iosxe': "banner = parse.find_objects('^banner')",
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
            'iosxe':"radius = parse.find_objects('^radius-server|^radius\sserver')"
        },

        'http_server':{
            'name': "HTTP server",
            'support':"",
            'translatable':"",
            'regex': '^ip\shttp',
            'meraki': {
                'skip': True
            },
            'iosxe': "http_server = parse.find_objects('^ip\shttp')",
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
            'iosxe': """
stack = parse.find_objects('^switch')
if len(stack) == 1:
    stack = []
"""
        },

        'mab_vlan_mac':{
            'name': "MAB VLAN MAC Auth",
            'support':"",
            'translatable':"",
            'regex': '^mab\srequest\sformat',
            'meraki': {
                'skip': True
            },
            'iosxe': "mab_vlan_mac = parse.find_objects('^mab\srequest\sformat')",
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
            'iosxe': "vlan = parse.find_objects('^vlan')",
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
            'iosxe': "vmps = parse.find_objects('^vmps')",
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
            'iosxe': "uplinkfast = parse.find_objects('^spanning-tree\suplinkfast')",
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
            'iosxe': "backbonefast = parse.find_objects('^spanning-tree\sbackbonefast')",
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
            'iosxe': "loopguard = parse.find_objects('spanning-tree\sloopguard')",
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
            'iosxe': "dhcp_snooping = parse.find_objects('ip\sdhcp\ssnooping')",
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
            'iosxe': "ip_source_guard = parse.find_objects('ip\ssource\sbinding')"
        },

        'arp_inspection':{
            'name': "ARP Inspection",
            'support':"✓",
            'translatable':"",
            'regex': '^ip\sarp\sinspection',
            'meraki': {
                'skip': True
            },
            'iosxe': "arp_inspection = parse.find_objects('^ip\sarp\sinspection')",
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
            'iosxe': "arp_acl = parse.find_objects('^arp\saccess-list')",
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
            'iosxe': "psp = parse.find_objects('^psp')",
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
            'iosxe': "udld = parse.find_objects('^udld')",
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
            'iosxe': "logging = parse.find_objects('^logging')",
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
            'iosxe': "ip_sla = parse.find_objects('^ip\ssla')",
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
            'iosxe': "multicast_igmp = parse.find_objects('^ip\sigmp')",
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
            'iosxe': "multicast_pim = parse.find_objects('^ip\spim')"
        },

        'static_routing':{
            'name': "Static routing",
            'support':"✓",
            'translatable':"✓",
            'regex': '^ip\sroute|^ip\sdefault-gateway',
            'iosxe': """
static_routing = list()
route_obj_list = parse.find_objects('^ip\sroute\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
for route_obj in route_obj_list:
    net = route_obj.re_match_typed('^ip\sroute\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
    mask = route_obj.re_match_typed('^ip\sroute\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
    gw = route_obj.re_match_typed('^ip\sroute\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
    import ipaddress
    subnet = str(ipaddress.ip_network(net + '/' + mask, strict=False))
    static_routing.append({'net': net, 'mask': mask, 'gw': gw, 'subnet': subnet})
route_obj_list = parse.find_objects('^ip\sdefault-gateway\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
if len(route_obj_list) == 1:
    import ipaddress
    subnet = str(ipaddress.ip_network('0.0.0.0/0', strict=False))
    gw = route_obj_list[0].re_match_typed('^ip\sdefault-gateway\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
    static_routing.append({'net': '0.0.0.0', 'mask': '0.0.0.0', 'gw': gw, 'subnet': subnet})
""",
            'meraki': {
                'skip': 'post_ports',
                'post_process': """
for route in switch_dict['static_routing']:
    if route['subnet'] == '0.0.0.0/0':
        default_route = route
        return_vals = ['default_route']
""",
                'post_ports_process': """
for route in switch_dict['static_routing']:
    if not route['subnet'] == '0.0.0.0/0':
        if 'switchStackId' in switch_dict.keys():
            dashboard.switch.createNetworkSwitchStackRoutingStaticRoute(switch_dict['networkId'],switch_dict['switchStackId'],route['subnet'],route['gw'])
        else:
            if len(sw_list) == 1:
                dashboard.switch.createDeviceSwitchRoutingStaticRoute(sw_list[0],route['subnet'],route['gw'])
"""
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
            'iosxe': "ipv6 = parse.find_objects('^ipv6')"
        },

        'rip':{
            'name': "RIP",
            'support':"",
            'translatable':"",
            'regex': '^router rip',
            'meraki': {
                'skip': True
            },
            'iosxe': "rip = parse.find_objects('^router rip')",
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
            'iosxe': "eigrp = parse.find_objects('^router eigrp')",
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
            'iosxe': "ospf = parse.find_objects('^router ospf')",
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
            'iosxe': "ospfv3 = parse.find_objects('^router ospfv3')",
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
            'iosxe': "bgp = parse.find_objects('^router bgp')",
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
            'iosxe': "isis = parse.find_objects('^router isis')",
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
            'iosxe': "vrf = parse.find_objects('^vrf')",
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
            'iosxe': "name = child.re_match_typed(regex=r'\sdescription\s+(\S.+)')"
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
            'iosxe': """
shut = child.re_match_typed(regex=r'\s(shutdown)')
active = 'true' if shut == '' else 'false'
"""
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
            'iosxe': "speed = child.re_match_typed(regex=r'\sspeed\s+(\S.*)')"
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
            'iosxe': "duplex = child.re_match_typed(regex=r'\sduplex\s+(\S.+)')"
        },

        'linkNegotiation': {
            'iosxe': "",
            'regex': '',
            'meraki': {
                'skip': 'post_process',
                'default': 'Auto negotiate',
                'post_process': """
linkNegotiation = ''
try:
    speed = int(intf_settings['speed'])
    if speed < 1000:
        linkNegotiation += str(speed)+' Megabit '
    else:
        linkNegotiation += str(int(speed/1000))+' Gigabit '
    try:
        duplex = intf_settings['duplex']
        match duplex:
            case 'half':
                linkNegotiation += 'half duplex (forced)'
            case 'full':
                linkNegotiation += 'full duplex (forced)'
    except KeyError:
        linkNegotiation += '(auto)'
except:
    linkNegotiation = 'Auto negotiate'
"""
            }
        },

        'type': {
            'name': "Port Type",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sswitchport\smode(?:\s\S+-\S+)?\s(access|trunk|host)',
            'meraki': {
                'skip': False,
                'default': 'trunk'
            },
            'iosxe': """
type = child.re_match_typed(regex=r'\sswitchport\smode(?:\s\S+-\S+)?\s(access|trunk|host)')
type = 'access' if type == 'host' else type
"""
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
            'iosxe': "poeEnabled = not child.re_match_typed(regex=r'\spower\sinline\s+(\S.+)')=='never'"
        },

        'allowedVlans': {
            'name': "Allowed VLANs",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sswitchport\strunk\sallowed\svlan\s+(\S.*)',
            'meraki': {
                'skip': False
            },
            'iosxe': "allowedVlans = child.re_match_typed(regex=r'\sswitchport\strunk\sallowed\svlan\s+(\S.*)')"
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
            'iosxe': "vlan = child.re_match_typed(regex=r'\sswitchport\strunk\snative\svlan\s+(\S.*)')"
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
            'iosxe': "vlan = child.re_match_typed(regex=r'\sswitchport\svlan\s+(\S.*)')"
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
            'iosxe': "voiceVlan = child.re_match_typed(regex=r'\sswitchport\svoice\svlan\s+(\S.*)')"
        },

        'isolationEnabled': {
            'name': "Private VLAN",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sswitchport\smode\sprivate-vlan?(\S.*)',
            'meraki': {
                'skip': False,
                'default': False
            },
            'iosxe': "isolationEnabled = True if not child.re_match_typed(regex=r'\sswitchport\smode\sprivate-vlan?(\S.*)') == '' else False",
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
                'post_process':"""
l3_interface = True
return_vals=['l3_interface']
""",
                'post_ports_process': """
conf_ports = list()
unconf_ports = list()
temp_payload = {}
payload = {}

l3_ports = [v for k, v in port_dict.items() if 'Vlan' in k]
if debug:
    print(f'l3_ports = {l3_ports}')
x = 0
while x < len(l3_ports):
    if debug:
        print(f'l3_ports[{x}] = {l3_ports[x]}')
        print(f'l3_ports[{x}][meraki_args] = ')
        print(l3_ports[x]['meraki_args'])
    ma = l3_ports[x]['meraki_args']
    if 'defaultGateway' in ma[4].keys():
        try:
            if 'switchStackId' in switch_dict:
                dashboard.switch.createNetworkSwitchStackRoutingInterface(ma[0],ma[1],ma[2],ma[3],**ma[4])
            else:
                if unified_os:
                    import requests
                    import json
                    import os
                    url = "https://api.meraki.com/api/v1/devices/" + sw_list[0] + "/switch/routing/interfaces"
                    temp_payload = {
                        "name": ma[2],
                        "switchPortId": "1",
                        "vlanId": ma[3],
                        "staticV4Dns1": "8.8.8.8",
                        "staticV4Dns2": "8.8.4.4"
                    }
                    payload = temp_payload | ma[4]
                    pretty_payload = json.dumps(payload, indent=4)
                    data = pretty_payload.rstrip(os.linesep+'}') + ',' + os.linesep + '    "uplinkV4": true' + os.linesep + '}'
                    headers = {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-Cisco-Meraki-API-Key": meraki_api_key
                    }
                    response = requests.request('POST', url, headers=headers, data = data)
                    if debug:
                        print(response.text.encode('utf8'))
                else:
                    dashboard.switch.createDeviceSwitchRoutingInterface(sw_list[0],ma[2],vlanId=ma[3],**ma[4])
            conf_ports.append(ma[2])
        except:
            print(f'We had an issue creating {ma[2]}.')
            unconf_ports.append(ma[2])
        dg = x
        break
    x+=1
x = 0
while x < len(l3_ports):
    if not x == dg:
        ma = l3_ports[x]['meraki_args']
        try:
            if 'switchStackId' in switch_dict.keys():
                dashboard.switch.createNetworkSwitchStackRoutingInterface(ma[0],ma[1],ma[2],ma[3],**ma[4])
            else:
                dashboard.switch.createDeviceSwitchRoutingInterface(swlist[0],name=ma[2],vlanId=ma[3],**ma[4])
            conf_ports.append(ma[2])
        except:
            print(f'We had an issue creating {ma[2]}.')
            unconf_ports.append(ma[2])
    x+=1
return_vals = ['l3_ports','conf_ports','unconf_ports']
"""
            },
            'iosxe': "l3_interface = child.re_match_typed(regex=r'\sip\saddress\s(\S.*)')"
        },

        'root_guard': {
            'name': "STP Root Guard",
            'support':"✓",
            'translatable':"✓",
            'iosxe': "root_guard = 'yes'",
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
            'iosxe': "loop_guard = 'yes'",
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
            'iosxe': "bpdu_guard =  'yes'",
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
                'post_process': """
stpGuard = 'disabled'
try:
    if intf_settings['root_guard'] == 'yes':
        stpGuard = 'root guard'
except:
    pass
try:
    if intf_settings['loop_guard'] == 'yes':
        stpGuard = 'loop guard'
except:
    pass
try:
    if intf_settings['bpdu_guard'] == 'yes':
        stpGuard = 'bpdu guard'
except:
    pass
if debug:
    print(f'stpGuard = {stpGuard}')
""",
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
            'iosxe': "pruning = child.re_match_typed(regex=r'\sswitchport\strunk\spruning?(\S.*)')",
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
            'iosxe': "stp_port = child.re_match_typed(regex=r'\sspanning-tree\sport-priority?(\S.*)')"
        },

        'portfast': {
            'name': "STP Portfast",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sspanning-tree\sportfast?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "portfast = child.re_match_typed(regex=r'\sspanning-tree\sportfast?(\S.*)')",
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
            'iosxe': "storm_control = child.re_match_typed(regex=r'\sstorm-control?(\S.*)')",
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
            'iosxe': "protected = child.re_match_typed(regex=r'\sswitchport\sprotected?(\S.*)')",
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
            'iosxe': "port_security = child.re_match_typed(regex=r'\sswitchport\sport-security?(\S.*)')"
        },

        'port_udld': {
            'name': "Port UDLD",
            'support':"✓",
            'translatable':"",
            'regex': r'\sudld\sport?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "port_udld = child.re_match_typed(regex=r'\sudld\sport?(\S.*)')"
        },

        'lldp': {
            'name': "LLDP",
            'support':"",
            'translatable':"",
            'regex': r'\slldp?(\S.*)',
            'meraki': {
                'skip': True
            },
            'iosxe': "lldp = child.re_match_typed(regex=r'\slldp?(\S.*)')",
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
            'iosxe': "ipv6 = child.re_match_typed(regex=r'\sipv6?(\S.*)')",
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
            'iosxe': "directed_broadcast = child.re_match_typed(regex=r'\sip\sdirected-broadcast?(\S.*)')"
        },

        'etherchannel_cisco': {
            'name': "Etherchannel Classic",
            'support':"",
            'translatable':"",
            'regex': r'^\schannel-group\s\d+\smode\s(on)',
            'meraki': {
                'skip': True
            },
            'iosxe': "etherchannel_cisco = 'on'",
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
            'iosxe': "etherchannel_pagp = child.re_match_typed('^\schannel-group\s\d+\smode\s(auto|desirable)')",
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
            'iosxe': "etherchannel_lacp = child.re_match_typed('^\schannel-group\s(\d+)')"
        },

        'etherchannel': {
            'iosxe': "",
            'regex': '',
            'meraki': {
                'skip': 'post_ports',
                'post_process': """
if 'etherchannel_lacp' in intf_settings:
    if debug:
        print('etherchannel_lacp = ' + intf_settings['etherchannel_lacp'])
    group = intf_settings['etherchannel_lacp']
    serial = sw_list[switch_num]
    portId = intf_settings['port']
    if debug:
        print('group = ' + group + ', switch_num = ' + str(switch_num) + ', serial = ' + serial + ', portId = ' + portId)
    etherchannel = {'group': group, 'switch_num': switch_num, 'serial': serial, 'portId': portId}
    if debug:
        print(etherchannel)
    return_vals = ['etherchannel']
    if debug:
        print(return_vals)
""",
            'post_ports_process': """
if debug:
    print(f'In post_ports_process, post_ports_list = {post_ports_list}')
    print(f'Length of post_ports_list is {len(post_ports_list)}')
# Get a list of array positions where 'etherchannel' appears in our post_ports_list
channel_positions = [i for i in range(len(post_ports_list)) if post_ports_list[i][0] == 'etherchannel']
if debug:
    print(f'channel_positions = {channel_positions}')
# Create a dictionary of lists to hold the data needed to create each etherchannel
channel_dict = dict(list())
channel_port_dict = {}
#action_list = list()
x = 0
# Loop through the relevant positions in the post_ports_list, and append the required data
# to the dictionary of lists that holds the data for each etherchannel
while x < len(channel_positions):
    if debug:
        print(f'post_ports_list[channel_positions[x]][1] = {post_ports_list[channel_positions[x]][1]}')
    group = post_ports_list[channel_positions[x]][1]['group']
    # We need to remove 'group' from the dictionary of values now before adding the
    # other dictionary entries to the list that Dashboard will process for this
    # etherchannel group
    post_ports_list[channel_positions[x]][1].pop('group')
    post_ports_list[channel_positions[x]][1].pop('switch_num')
    if debug:
        print(f'group = {group}')
    if group not in channel_dict.keys():
        channel_dict[group] = []
    # Append the 'serial' and 'port' key, value pairs to the switchPorts list for this
    # etherchannel group
    channel_dict[group].extend([post_ports_list[channel_positions[x]][1]])
    if debug:
        print(f'In loop x = {x}, channel_dict = {channel_dict}')
    x+=1
if debug:
    print(f'channel_dict = {channel_dict}')
return_vals = list()
if debug:
    print(f'len(channel_dict) = {len(channel_dict)}')
key_list =list(channel_dict.keys())
x = 0
while x < len(key_list):
    if debug:
        print(f'key = {key_list[x]}, channel_dict[{key_list[x]}] = {channel_dict[key_list[x]]}')
        print(f'switchPorts = {channel_dict[key_list[x]]}')
        print('networkId = ' + returns_dict['networkId'])
    interface_descriptor = 'Port-channel' + key_list[x]
    channel_port_dict[interface_descriptor] = port_dict[interface_descriptor]
    channel_port_dict[interface_descriptor]['meraki_args'] = [returns_dict['networkId'],channel_dict[key_list[x]]]
    try:
        #action_list.append(dashboard.switch.createNetworkSwitchLinkAggregation(returns_dict['networkId'], switchPorts = channel_dict[key]))
        r = dashboard.switch.createNetworkSwitchLinkAggregation(returns_dict['networkId'], switchPorts = channel_dict[key_list[x]])
        if debug:
            print(f'channel_port_dict = {channel_port_dict}')
        channel_port_dict[interface_descriptor]['id'] = r['id']
        if debug:
            print(f'channel_port_dict[{interface_descriptor}] = {channel_port_dict[interface_descriptor]}')
            print(f'Dashboard response was {r}')
    except:
        print(f'Exception in port-channel')
        x+=1
        continue
    x+=1
return_vals = ['channel_port_dict']
"""
            }
        }
    },
    'layer3': {

        'interfaceIp': {
            'iosxe': "",
            'regex': '',
            'meraki': {
                'skip': 'post_process',
                'post_process': """
interfaceIp = ''
if 'l3_interface' in intf_settings.keys():
    import re
    if not intf_settings['l3_interface'] == '':
        interfaceIp = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', intf_settings['l3_interface'])[0]
"""
            }
        },

        'subnet': {
            'iosxe': "",
            'regex': '',
            'meraki': {
                'skip': 'post_process',
                'post_process': """
if 'l3_interface' in intf_settings.keys():
        import re
        subnet = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', intf_settings['l3_interface'])[0]
        import ipaddress
        if debug:
            print(f'intf_settings = {intf_settings}')
        subnet = str(ipaddress.ip_network(intf_settings['interfaceIp'] + '/' + subnet, strict=False))
        defaultGateway = switch_dict['default_route']['gw']
        if ipaddress.ip_address(defaultGateway) in ipaddress.ip_network(subnet):
            if debug:
                print(f'defaultGateway = {defaultGateway}')
            return_vals = ['defaultGateway']
"""
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
  },
    "C9300X-NM-8Y":
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
    r'TenGigabitEthernet\d/1/8',
    r'TwentyFiveGigE\d/1/1',
    r'TwentyFiveGigE\d/1/2',
    r'TwentyFiveGigE\d/1/3',
    r'TwentyFiveGigE\d/1/4',
    r'TwentyFiveGigE\d/1/5',
    r'TwentyFiveGigE\d/1/6',
    r'TwentyFiveGigE\d/1/7',
    r'TwentyFiveGigE\d/1/8',
    r'HundredGigE\d/1/1',
    r'HundredGigE\d/1/2'
    ],
    "description": "Catalyst 9300X 8 x 100G/25G/10G multi-rate SFP Network Module"
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
