'''
#####################################################################################

This dictionary contains many Catalyst switch & port configuration elements,
along with their CiscoConfParse IOSXE parsing matches, and the values to
pass back for the element.

There are currently two sub-dictionaries: 'switch' & 'port'.

#####################################################################################

Elements in the 'switch' and 'port' sub-dictionaries have multiple keys within them:
'name' & 'support', 'translatable', 'regex', 'iosxe', 'url' & 'note'.

The 'name' value is used for reporting on the feature.

The 'support' value indicates whether or not the feature is supported in a similar
way on a Meraki device.

The 'translatable' value indicates whether or not the merakicat translator can
translate the feature configuration to a Meraki device.

The 'regex' value is the CiscoConfParse IOSXE parsing regex match for this element.

The 'iosxe' value is the python code (as a string) to extract information from the
switch config and set a value based on that information.

The 'url' value is an optional key/value pair that directs the user to additional
information within documentation on the Meraki site.

The 'note' value is an optional key/value pair that gives the user to a short
note regarding the feature support, and can be used as the link text for the url
value above.

#####################################################################################
'''

check_pedia = {
    'switch': {
        "hostname":{
            'name': "Hostname",
            'support':"✓",
            'translatable':"✓",
            'iosxe':"\
\
hostname = parse.find_objects('^hostname')\n\
host_name = hostname[0].re_match_typed(r'^hostname\s+(\S+)',default='')\n"
            },
        "interface":{
            'name': "Interface",
            'support':"✓",
            'translatable':"✓",
            'iosxe':"interface = parse.find_objects('^interface')\n"
            },
        "vtp":{
            'name': "VTP",
            'support':"",
            'translatable':"",
            'iosxe': "vtp = parse.find_objects('^vtp')\n",
            'url':"https://documentation.meraki.com/MS/Port_and_VLAN_Configuration/Integrating_the_MS_Access_Switch_into_a_Cisco_VTP_domain",
            'note':"Not required"
            },
        "mls":{
            'name': "QoS",
            'support':"",
            'translatable':"",
            'iosxe': "mls = parse.find_objects('^mls')\n"
            },
        "spanning":{
            'name':"Spanning Tree",
            'support':"",
            'translatable':"",
            'iosxe': "spanning = parse.find_objects('^spanning')\n",
            'url':"https://documentation.meraki.com/MS/Port_and_VLAN_Configuration/Configuring_Spanning_Tree_on_Meraki_Switches_(MS)",
            'note':"Only Supports RSTP"
        },
        "snmp":{
            'name': "SNMP",
            'support':"",
            'translatable':"",
            'iosxe':"parse.find_objects('^snmp')\n"
            },
        "logging_host":{
            'name': "Syslog",
            'support':"",
            'translatable':"",
            'iosxe':"logging_host = parse.find_objects('^logging')\n"
            },
        "ntp":{
            'name':"NTP",
            'support':"",
            'translatable':"",
            'iosxe':"ntp = parse.find_objects('^ntp')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Configured by default"
            },
        "access_list":{
            'name': "Access-List",
            'support':"",
            'translatable':"",
            'iosxe': "access_list = parse.find_objects('^access-list')\n"
            },
        "extended_access_list":{
            'name': "Extended ACL",
            'support':"",
            'translatable':"",
            'iosxe': "extended_access_list = parse.find_objects('^ip\saccess-list')\n"
            },
        "port_mirror":{
            'name': "Port mirroring",
            'support': "✓",
            'translatable':"",
            'iosxe': "port_mirror = parse.find_objects('^monitor')\n"
            },
        "aaa":{
            'name': "AAA",
            'support':"",
            'translatable':"",
            'iosxe': "aaa = parse.find_objects('^aaa')\n",
            'url':"https://documentation.meraki.com/General_Administration/Managing_Dashboard_Access/Managing_Dashboard_Administrators_and_Permissions",
            'note':"Built in Meraki dashboard"
            },
        "netflow":{
            'name': "NetFlow",
            'support':"",
            'translatable':"",
            'iosxe': "netflow = parse.find_objects('^flow\sexporter')\n",
            'url':"https://documentation.meraki.com/MX/Monitoring_and_Reporting/NetFlow_Overview",
            'note':"Currently supported on MX only"
            },
        "dhcp":{
            'name':"DHCP server",
            'support':"",
            'translatable':"",
            'iosxe':"dhcp = parse.find_objects('^ip\sdhcp\spool')\n"
            },
        "banner":{
            'name': "Banner",
            'support':"",
            'translatable':"",
            'iosxe': "banner = parse.find_objects('^banner')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not required"
            },
        "radius":{
            'name':"radius",
            'support':"",
            'translatable':"",
            'iosxe':"radius = parse.find_objects('^radius-server')\n"
            },
        "radius2":{
            'name':"radius",
            'support':"",
            'translatable':"",
            'iosxe':"radius2 = parse.find_objects('^radius\sserver')\n"
            },
        "http_server":{
            'name': "HTTP server",
            'support':"",
            'translatable':"",
            'iosxe': "http_server = parse.find_objects('^ip\shttp')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported"
            },
        "stack":{
            'name': "Stack",
            'support':"✓",
            'translatable':"✓",
            'iosxe': "stack = parse.find_objects('^switch')\n"
            },
        "mab_vlan_mac":{
            'name': "MAB VLAN MAC Auth",
            'support':"",
            'translatable':"",
            'iosxe': "mab_vlan_mac = parse.find_objects('^mab\srequest\sformat')\n",
            'url':"https://documentation.meraki.com/MS/Access_Control/MS_Switch_Access_Policies_(802.1X)",
            'note':"MAB with RADIUS is supported"
            },
        "vlan":{
            'name': "Layer 2 VLAN",
            'support':"",
            'translatable':"",
            'iosxe': "vlan = parse.find_objects('^vlan')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Configured by default"
            },
        "vpms":{
            'name': "VPMS",
            'support':"",
            'translatable':"",
            'iosxe': "vpms = parse.find_objects('^vpms')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported as it is dated technology"
            },
        "uplinkfast":{
            'name': "STP Uplinkfast",
            'support':"",
            'translatable':"",
            'iosxe': "uplinkfast = parse.find_objects('^spanning-tree\suplinkfast')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported"
            },
        "backbonefast":{
            'name': "STP Backbonefast",
            'support':"",
            'translatable':"",
            'iosxe': "backbonefast = parse.find_objects('^spanning-tree\sbackbonefast')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported"
            },
        "loopguard":{
            'name': "STP Loopguard",
            'support':"",
            'translatable':"",
            'iosxe': "loopguard = parse.find_objects('spanning-tree\sloopguard')\n"
            },
        "dhcp_snooping":{
            'name': "DHCP Snooping",
            'support':"",
            'translatable':"",
            'iosxe': "dhcp_snooping = parse.find_objects('ip\sdhcp\ssnooping')\n",
            'note':"Not Supported"
            },
        "ip_source_guard":{
            'name': "IP Source Binding",
            'support':"",
            'translatable':"",
            'iosxe': "ip_source_guard = parse.find_objects('ip\ssource\sbinding')\n"
            },
        "arp_inspection":{
            'name': "ARP Inspection",
            'support':"",
            'translatable':"",
            'iosxe': "arp_inspection = parse.find_objects('^ip\sarp\sinspection')\n"
            },
        "arp_acl":{
            'name': "ARP Access-list",
            'support':"",
            'translatable':"",
            'iosxe': "arp_acl = parse.find_objects('^arp\saccess-list')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported"
            },
        "psp":{
            'name': "Protocol Storm Protection",
            'support':"",
            'translatable':"",
            'iosxe': "psp = parse.find_objects('^psp')\n",
            'url': "https://documentation.meraki.com/MS",
            'note':"Not Supported"
            },
        "udld":{
            'name': "UDLD",
            'support':"",
            'translatable':"",
            'translateable':"",
            'iosxe': "udld = parse.find_objects('^udld')\n"
            },
        "logging":{
            'name': "Logging",
            'support':"",
            'translatable':"",
            'translateable':"",
            'iosxe': "logging = parse.find_objects('^logging')\n"
            },
        "ip_sla":{
            'name': "IP SLA",
            'support':"",
            'translatable':"",
            'translateable':"",
            'iosxe': "ip_sla = parse.find_objects('^ip\ssla')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported"
            },
        "multicast_igmp":{
            'name': "Multicast IGMP",
            'support':"",
            'translatable':"",
            'translateable':"",
            'iosxe': "multicast_igmp = parse.find_objects('^ip\sigmp')\n"
            },
        "multicast_pim":{
            'name': "Multicast PIM",
            'support':"",
            'translatable':"",
            'translateable':"",
            'iosxe': "multicast_pim = parse.find_objects('^ip\spim')\n"
            },
        "static_routing":{
            'name': "Static routing",
            'support':"",
            'translatable':"",
            'translateable':"",
            'iosxe': "static_routing = parse.find_objects('^ip\sroute')\n"
            },
        "ipv6":{
            'name': "IPv6",
            'support':"",
            'translatable':"",
            'translateable':"",
            'iosxe': "ipv6 = parse.find_objects('^ipv6')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported"
            },
        "rip":{
            'name': "RIP",
            'support':"",
            'translatable':"",
            'translateable':"",
            'iosxe': "rip = parse.find_objects('^router rip')\n",
            'url':"https://documentation.meraki.com/MS/Layer_3_Switching/MS_Layer_3_Switching_and_Routing",
            'note':"Not Supported"
            },
        "eigrp":{
            'name': "EIGRP",
            'support':"",
            'translatable':"",
            'translateable':"",
            'iosxe': "eigrp = parse.find_objects('^router eigrp')\n",
            'url':"https://documentation.meraki.com/MS/Layer_3_Switching/MS_Layer_3_Switching_and_Routing",
            'note':"Not Supported"
            },
        "ospf":{
            'name': "OSPFv2",
            'support':"",
            'translatable':"",
            'translateable':"",
            'iosxe': "ospf = parse.find_objects('^router ospf')\n",
            'url':"https://documentation.meraki.com/MS/Layer_3_Switching/MS_Layer_3_Switching_and_Routing",
            'note':"Supported on MS250 and above"
            },
        "ospfv3":{
            'name': "OSPFv3",
            'support':"",
            'translatable':"",
            'translateable':"",
            'iosxe': "ospfv3 = parse.find_objects('^router ospfv3')\n",
            'url':"https://documentation.meraki.com/MS/Layer_3_Switching/MS_Layer_3_Switching_and_Routing",
            'note':"Not Supported"
            },
        "bgp":{
            'name': "BGP",
            'support':"",
            'translatable':"",
            'translateable':"",
           'iosxe': "bgp = parse.find_objects('^router bgp')\n",
            'url':"https://documentation.meraki.com/MX/Networks_and_Routing/Border_Gateway_Protocol_(BGP)",
            'note':"Currently supported on MX only"
            },
        "isis":{
            'name': "IS-IS",
            'support':"",
            'translatable':"",
            'translateable':"",
            'iosxe': "isis = parse.find_objects('^router isis')\n",
            'url':"https://documentation.meraki.com/MS/Layer_3_Switching/MS_Layer_3_Switching_and_Routing",
            'note':"Not Supported"
            },
        "vrf": {
            'name': "VRF",
            'support':"",
            'translatable':"",
            'iosxe': "vrf = parse.find_objects('^vrf')\n",
            'url':"https://documentation.meraki.com/MS/Layer_3_Switching/MS_Layer_3_Switching_and_Routing",
            'note':"Not Supported"
            },
        "Directed Broadcast":{
            'name': "Directed Broadcast",
            'support':"",
            'translatable':"",
            'url':"https://documentation.meraki.com/MS/Layer_3_Switching/MS_Multicast_Routing_Overview",
            'note':"Not Supported"
            }
    },
    'port': {
        "private_vlan": {
            'name': "Private VLAN",
            'regex': r'\sswitchport\smode\sprivate-vlan?(\S.*)',
            'iosxe': "private_vlan = config_det.re_match_typed(regex=r'\sswitchport\smode\sprivate-vlan?(\S.*)')\n",
            'url':"https://documentation.meraki.com/MS/Port_and_VLAN_Configuration/Restricting_Traffic_with_Isolated_Switch_Ports",
            'note':"Port Isolation can be used"
            },
        "pruning": {
            'name': "Pruning",
            'support':"",
            'translatable':"",
            'regex': r'\sswitchport\strunk\spruning?(\S.*)',
            'iosxe': "pruning = config_det.re_match_typed(regex=r'\sswitchport\strunk\spruning?(\S.*)')\n",
            'url':"https://documentation.meraki.com/General_Administration/Tools_and_Troubleshooting/Fundamentals_of_802.1Q_VLAN_Tagging",
            'note':"Not required"
            },
        "voice_vlan": {
            'name': "Voice VLAN",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sswitchport\svoice?(\S.*)',
            'iosxe': "voice_vlan = config_det.re_match_typed(regex=r'\sswitchport\svoice?(\S.*)')\n"
            },
        "data_vlan": {
            'name': "Data VLAN",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sswitchport\saccess?(\S.*)',
            'iosxe': "data_vlan = config_det.re_match_typed(regex=r'\sswitchport\saccess?(\S.*)')\n"
            },
        "stp_port": {
            'name': "STP Port Priority",
            'support':"",
            'translatable':"",
            'regex': r'\sspanning-tree\sport-priority?(\S.*)',
            'iosxe': "stp_port = config_det.re_match_typed(regex=r'\sspanning-tree\sport-priority?(\S.*)')\n"
            },
        "portfast": {
            'name': "STP Portfast",
            'support':"",
            'translatable':"",
            'regex': r'\sspanning-tree\sportfast?(\S.*)',
            'iosxe': "portfast = config_det.re_match_typed(regex=r'\sspanning-tree\sportfast?(\S.*)')\n"
            },
        "root_guard": {
            'name': "STP RootGuard",
            'support':"✓",
            'translatable':"",
            'regex': r'\sspanning-tree\sguard\sroot?(\S.*)',
            'iosxe': "root_guard = config_det.re_match_typed(regex=r'\sspanning-tree\sguard\sroot?(\S.*)')\n"
            },
        "loop_guard": {
            'name': "STP Loop Guard",
            'support':"✓",
            'translatable':"",
            'regex': r'\sspanning-tree\sguard\sloop?(\S.*)',
            'iosxe': "loop_guard = config_det.re_match_typed(regex=r'\sspanning-tree\sguard\sloop?(\S.*)')\n"
            },
        "bpdu_guard": {
            'name': "STP BPDU Guard",
            'support':"✓",
            'translatable':"",
            'regex': r'\sspanning-tree\sbpduguard?(\S.*)',
            'iosxe': "bpdu_guard = config_det.re_match_typed(regex=r'\sspanning-tree\sbpduguard?(\S.*)')\n"
            },
        "flex_links": {
            'name': "Flex Links",
            'support':"",
            'translatable':"",
            'regex': r'\sswitchport\sbackup\sinterface?(\S.*)',
            'iosxe': "flex_links = config_det.re_match_typed(regex=r'\sswitchport\sbackup\sinterface?(\S.*)')\n"
            },
        "storm_control": {
            'name': "Storm Control",
            'support':"",
            'translatable':"",
            'regex': r'\sstorm-control?(\S.*)',
            'iosxe': "storm_control = config_det.re_match_typed(regex=r'\sstorm-control?(\S.*)')\n",
            'url':"https://documentation.meraki.com/MS/Other_Topics/Storm_Control_for_MS",
            'note':"Network-wide"
            },
        "protected": {
            'name': "Protected",
            'support':"",
            'translatable':"",
            'regex': r'\sswitchport\sprotected?(\S.*)',
            'iosxe': "protected = config_det.re_match_typed(regex=r'\sswitchport\sprotected?(\S.*)')\n"
            },
        "port_security": {
            'name': "Port Security",
            'support':"✓",
            'translatable':"",
            'regex': r'\sswitchport\sport-security?(\S.*)',
            'iosxe': "port_security = config_det.re_match_typed(regex=r'\sswitchport\sport-security?(\S.*)')\n"
            },
        "port_udld": {
            'name': "Port UDLD",
            'support':"✓",
            'translatable':"",
            'regex': r'\sudld\sport?(\S.*)',
            'iosxe': "port_udld = config_det.re_match_typed(regex=r'\sudld\sport?(\S.*)')\n"
            },
        "lldp": {
            'name': "LLDP",
            'support':"",
            'translatable':"",
            'regex': r'\slldp?(\S.*)',
            'iosxe': "lldp = config_det.re_match_typed(regex=r'\slldp?(\S.*)')\n",
            'url':"https://documentation.meraki.com/General_Administration/Other_Topics/LLDP_Support_on_Cisco_Meraki_Products#ms",
            'note':"Always on"
            },
        "ipv6": {
            'name': "IPv6",
            'support':"",
            'translatable':"",
            'regex': r'\sipv6?(\S.*)',
            'iosxe': "ipv6 = config_det.re_match_typed(regex=r'\sipv6?(\S.*)')\n",
            'url':"https://documentation.meraki.com/MS",
            'note':"Not Supported"
            },
        "etherchannel_type": {
            'name': "Etherchannel Type",
            'regex': r'^\schannel-group\s\d\smode\s+(\S.+)',
            'iosxe': "etherchannel_type = config_det.re_match_typed('^\schannel-group\s\d\smode\s+(\S.+)')\n"
            },
        "mode_access": {
            'name': "Access Port",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sswitchport\smode\saccess?(\S.*)',
            'iosxe': "mode_access = config_det.re_match_typed(regex=r'\sswitchport\smode\saccess?(\S.*)')\n"
            },
        "mode_trunk": {
            'name': "Trunk Port",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sswitchport\smode\strunk?(\S.*)',
            'iosxe': "mode_trunk = config_det.re_match_typed(regex=r'\sswitchport\smode\strunk?(\S.*)')\n"
            },
        "directed_broadcast": {
            'name': "IP Directed Broadcast",
            'regex': r'\sip\sdirected-broadcast?(\S.*)',
            'iosxe': "directed_broadcast = config_det.re_match_typed(regex=r'\sip\sdirected-broadcast?(\S.*)')\n"
            },
        "description": {
            'name': "Port Description",
            'support':"✓",
            'translatable':"✓",
            'regex': r'\sdescription?(\S.*)',
            'iosxe': "description = config_det.re_match_typed(regex=r'\sdescription?(\S.*)')\n"
        }
    }
}

def index_check_pedia():
    print("\n\n====================")
    print("Index of check_pedia:")
    print("====================\n")
    for key,value in check_pedia.items():
        print(key+":\n")
        for k,v in value.items():
            print(" - "+k+"\n")

if __name__ == '__main__':
    index_check_pedia()
