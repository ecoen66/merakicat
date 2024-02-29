import meraki
from meraki.config import SUPPRESS_LOGGING
from ciscoconfparse2 import CiscoConfParse
from collections import defaultdict
import os, requests, json, pprint, re
from mc_user_info import *

def Evaluate(sw_list, config_file):

    debug = DEBUG or DEBUG_TRANSLATOR
    
    port_dict = {}
    ## List of interfaces that are shut
    shut_interfaces = list()
    
    def read_Cisco_SW():
        ##Parsing the Cisco Catalyst configuration (focused on the interface config)
        if debug:
            print("-------- Reading <"+config_file+"> Configuration --------")
        parse = CiscoConfParse(config_file, syntax='ios', factory=True)
        
        switch_name = ""
        switch_name_obj = parse.find_objects('^hostname')
        if not switch_name_obj == []:
          switch_name = switch_name_obj[0].re_match_typed('^hostname\s(\S+)')
        
        Gig_uplink= list()
        Ten_Gig_uplink= list()
        Twenty_Five_Gig_uplink= list()
        Forty_Gig_uplink= list()
        Hundred_Gig_uplink= list()
        All_interfaces= defaultdict(list)
        
        # Grab all shutdown interfaces
        intf_for_test = parse.find_parent_objects([r'^interface', r'^\s+shutdown'])
        ## Remove the management, Loopback and VLAN interfaces from the intf_for_test list
        intf_for_test[:] = [y for y in intf_for_test if not (
            y.re_match_typed('^interface\s+(\S.*)$') == "GigabitEthernet0/0" or
            y.re_match_typed('^interface\s+(\S.*)$').startswith("Loopback") or
            y.re_match_typed('^interface\s+(\S.*)$').startswith("Vlan") or
            y.re_match_typed('^interface\s+(\S.*)$').startswith("AppGig"))]
        ## Test the remaining interfaces for shutdown and add to shut list
        for intf_obj in intf_for_test:
            shut_interfaces.append(intf_obj.re_match_typed('^interface\s+(\S.+?)$'))
        
        ## Select all interfaces
        intf = parse.find_objects('^interface')
        if debug:
            print(f"intf = {intf}")
        ## Remove the management, Loopback and VLAN interfaces from the interface list
        intf[:] = [x for x in intf if not (
            x.re_match_typed('^interface\s+(\S.*)$') == "GigabitEthernet0/0" or
            x.re_match_typed('^interface\s+(\S.*)$').startswith("Loopback") or
            x.re_match_typed('^interface\s+(\S.*)$').startswith("Vlan") or
            x.re_match_typed('^interface\s+(\S.*)$').startswith("AppGig"))]
        
##        print(f"These are the shut interfaces: {shut_interfaces}")
        
        for intf_obj in intf:
            ## Get the interface name
            intf_name = intf_obj.re_match_typed('^interface\s+(\S.*)$')
            #Only interface name will be used to catogrize different types of interfaces (downlink and uplink)
            only_intf_name = re.sub("\d+|\\/","",intf_name)
            Switch_module = intf_obj.re_match_typed('^interface\s\S+?thernet+(\d)')
            if Switch_module == "":
                Switch_module = intf_obj.re_match_typed('^interface\s\S+?GigE+(\d)')
            test_port_number = intf_obj.re_match_typed('^interface\s\S+?thernet+(\S+?)')
            if test_port_number == "":
                test_port_number = intf_obj.re_match_typed('^interface\s\S+?GigE+(\S+?)')
            
            All_interfaces[only_intf_name].append(intf_name)
            
            port_dict[intf_name] = {}
            port_dict[intf_name]['sw_module'] = "1"
            port_dict[intf_name]['sub_module'] = "0"
            port_dict[intf_name]['desc'] = ""
            port_dict[intf_name]['port'] = ""
            port_dict[intf_name]['mode'] = ""
            port_dict[intf_name]['mac'] = []
            port_dict[intf_name]['active'] = "true"
            
            try:
                port,sub_module = check(intf_name)
                port_dict[intf_name]['sub_module'] = sub_module
                if sub_module == "1":
                    if re.search(r'^GigabitEthernet',intf_name):
                        Gig_uplink.append(intf_name)
                    elif re.search(r'^TenGigabitEthernet',intf_name):
                        Ten_Gig_uplink.append(intf_name)
                    elif re.search(r'^TwentyFiveGigE',intf_name):
                        Twenty_Five_Gig_uplink.append(intf_name)
                    elif re.search(r'^FortyGigabitEthernet',intf_name):
                        Forty_Gig_uplink.append(intf_name)
                    elif re.search(r'^HundredGigabitEthernet',intf_name):
                        Hundred_Gig_uplink.append(intf_name)
                
                if debug:
                    print(f"Made it to Switch_module test")
                if Switch_module == 0:
                    port_dict[intf_name]['sw_module'] = 1
                if not Switch_module == "" and not Switch_module == 0:
                    port_dict[intf_name]['sw_module'] = Switch_module
                else:
                    pass
                
                port_dict[intf_name]['port'] = port
                port_dict[intf_name]['mac'].clear()
                ## check if the interface in the shutdown list then mark it as shutdown
                if intf_name in shut_interfaces:
                    port_dict[intf_name]['active'] = "false"
                
                if debug:
                    print("Checking children")
                int_fx = intf_obj.children
                if debug:
                    print(f"Children are: {int_fx}")
                ## Capture the configuration of the interface
                desc = ""
                port_mode = ""
                Vlan = ""
                Vlanv = ""
                port_sec_raw = ""
                trunk_native = ""
                trunk_v_allowed = ""
                speed = ""
                duplex = ""
                port_channel = ""
                max_mac = ""
                for child in int_fx:
                    try:
                        temp = child.re_match_typed(regex=r'\sdescription\s+(\S.+)')
                        if not temp == "":
                            desc = temp
                    except:
                        pass
                    try:
                        temp = child.re_match_typed(regex=r'\sswitchport\svoice\svlan\s+(\S.*)')
                        if not temp == "":
                            Vlanv = temp
                    except:
                        pass
                    try:
                        temp = child.re_match_typed(regex=r'\sswitchport\smode\s+(\S.+)')
                        if not temp == "":
                            port_mode = temp
                    except:
                        pass
                    try:
                        temp = child.re_match_typed(regex=r'\sswitchport\saccess\svlan\s+(\S.*)')
                        if not temp == "":
                            Vlan = temp
                    except:
                        pass
                    try:
                        temp = child.re_match_typed(regex=r'\sswitchport\sport-security\smac-address\ssticky\s+(\S.+)')
                        if not temp == "":
                            port_sec_raw = temp
                    except:
                        pass
                    try:
                        temp = child.re_match_typed(regex=r'\sswitchport\strunk\snative\svlan\s+(\S.*)')
                        if not temp == "":
                            trunk_native = temp
                    except:
                        pass
                    try:
                        temp = child.re_match_typed(regex=r'\sswitchport\strunk\sallowed\svlan\s+(\S.*)')
                        if not temp == "":
                            trunk_v_allowed = temp
                    except:
                        pass
                    try:
                        temp = child.re_match_typed(regex=r'\sspeed\s+(\S.*)')
                        if not temp == "":
                            speed = temp
                    except:
                        pass
                    try:
                        temp = child.re_match_typed(regex=r'\sduplex\s+(\S.+)')
                        if not temp == "":
                            duplex = temp
                    except:
                        pass
                    try:
                        temp = child.re_match_typed(regex=r'\schannel-group\s+(\d)')
                        if not temp == "":
                            port_channel = temp
                    except:
                        pass
                    try:
                        temp = child.re_match_typed(regex=r'\sswitchport\sport-security\smaximum\s+(\d)')
                        if not temp == "":
                            max_mac = temp
                    except:
                        pass
                
                if not desc == "":
                    port_dict[intf_name]['desc'] = desc
                port_dict[intf_name]['mode'] = "trunk"
                if not port_mode == "":
                    port_dict[intf_name]['mode'] = port_mode
                if not Vlan == "":
                    port_dict[intf_name]['data_Vlan'] = Vlan
                else:
                    if port_dict[intf_name]['mode'] == "access":
                        port_dict[intf_name]['data_Vlan'] = 1
                if not Vlanv == "":
                    port_dict[intf_name]['voice_Vlan'] = Vlanv
                if not port_sec_raw == "":
                    port_dict[intf_name]['mac'].append(mac_build(port_sec_raw))
                if not trunk_native == "":
                    port_dict[intf_name]['native'] = trunk_native
                if not trunk_v_allowed == "":
                    port_dict[intf_name]['trunk_allowed'] = trunk_v_allowed
                if not speed == "":
                    port_dict[intf_name]['speed'] = speed
                if not duplex == "":
                    port_dict[intf_name]['duplex'] = duplex
                if not port_channel == "":
                    port_dict[intf_name]['LACP_Group'] = port_channel
                if not max_mac == "":
                    port_dict[intf_name]['Port_Sec'] = max_mac
                else:
                    pass
            
            except:
                print(f"Error in ready interface {intf_name}")
                ## Add 1 to capture the next interface
                
        if debug:
            print(f"port_dict = {port_dict}\n")
        
        Uplink_list, Downlink_list, Other_list = split_down_up_link(All_interfaces,Gig_uplink)
        if debug:
            print(f"Uplink_list = {Uplink_list}\n")
            print(f"Downlink_list = {Downlink_list}\n")
            print(f"Other_list = {Other_list}\n")
            print(f"port_dict = {port_dict}\n")
            print(f"switch_name = {switch_name}\n")
        return Uplink_list, Downlink_list, Other_list, port_dict, switch_name
    
    def split_down_up_link(interfaces_list, Gig_uplink):
        Uplink_list=list()
        Downlink_list=list()
        Other_list =list()
        
        #Creating a copy of the interface list to avoid Runtime error
        interfaces_list_copy = interfaces_list.copy()
        if debug:
            print(f"interfaces_list = {interfaces_list}\n")
        for key, value in interfaces_list.items():
        #HundredGigabitEthernet ports stright away considered as uplinks
            if key == "HundredGigabitEthernet":
                for value in interfaces_list_copy["HundredGigabitEthernet"]:
                    Uplink_list.append(value)
        #FortyGigbitEthernet ports stright away considered as uplinks
            if key == "FortyGigabitEthernet":
                for value in interfaces_list_copy["FortyGigabitEthernet"]:
                    Uplink_list.append(value)
        #TwentyFiveGigbitEthernet ports stright away considered as uplinks
            if key == "TwentyFiveGigE":
                for value in interfaces_list_copy["TwentyFiveGigE"]:
                    Uplink_list.append(value)
        #TengigbitEthernet ports stright away considered as uplinks
            if key == "TenGigabitEthernet":
                for value in interfaces_list_copy["TenGigabitEthernet"]:
                    Uplink_list.append(value)
        #GigbitEthernet ports to be evaluated if has 1 in subnetwork module (x/1/x) then its uplink otherwise will be downlink
            if key == "GigabitEthernet":
               for value in interfaces_list_copy["GigabitEthernet"]:
                   if value in Gig_uplink:
                       Uplink_list.append(value)
                   if len(interfaces_list_copy["FastEthernet"]) > 4 and len(interfaces_list_copy["GigabitEthernet"]) < 5:
                       Uplink_list.append(value)
                   elif value not in Gig_uplink:
                       Downlink_list.append(value)
        #FastEthernet to be checked if has more than 4 ports in the list then they all downlink
            if key == "FastEthernet"  and len(interfaces_list_copy["FastEthernet"]) > 4:
                for value in interfaces_list["FastEthernet"]:
                    Downlink_list.append(value)
        #Single FastEthernet interface to be considered as others
            if key =="FastEthernet"  and len(interfaces_list_copy["FastEthernet"]) <=1:
                for value in interfaces_list_copy["FastEthernet"]:
                    Other_list.append(value)
            
            else:
                for value in interfaces_list_copy[key]:
                    if key=="HundredGigabitEthernet" or key=="FortyGigabitEthernet" or \
                        key=="TwentyFiveGigE" or key=="TenGigabitEthernet" or \
                        key=="GigabitEthernet" or key=="FastEthernet":
                        pass
                    else:
                        Other_list.append(value)
        return Uplink_list, Downlink_list, Other_list
    
    ## rebuild the mac address to match Meraki format
    def mac_build(my_str, group=2, char=':'):
        port_sec = re.findall(re.compile(r'[a-fA-F0-9.]{14}'), my_str)[0]
        p = re.compile(r'^[a-fA-F0-9.]{14}')
        new_p = re.sub("\.","",port_sec)
        my_str = str(new_p)
        
        last = char.join(my_str[i:i+group] for i in range(0, len(my_str), group))
        return last
    
    ## Extract out the details of the switch module and the port number
    def check(intf):
        if debug:
            print(f"Checking interface {intf}.")
       # intf_rgx = re.compile(r'^interface GigabitEthernet(\d+)\/(\d+)\/(\d+)$')
        obj = re.search(r'(?:Ethernet|GigE)(\d+)\/(\d+)\/(\d+)$',intf)
        if debug:
            print(f"obj.group(0) = {obj.group(0)}")
            print(f"obj.group(1) = {obj.group(1)}")
            print(f"obj.group(2) = {obj.group(2)}")
            print(f"obj.group(3) = {obj.group(3)}")
        port = obj.group(3)
        Sub_module = obj.group(2)
        
        return port,Sub_module
    
    Uplink_list, Downlink_list, Other_list, port_dict, switch_name  = read_Cisco_SW()
    return Uplink_list, Downlink_list, Other_list, port_dict, switch_name


def Meraki_config_down(dashboard,sw_list,port_dict,Downlink_list,switch_name):
    
    debug = DEBUG or DEBUG_TRANSLATOR
    
    configured_ports = defaultdict(list)
    unconfigured_ports = defaultdict(list)
    urls = list()
    
    
    ## Loop to go through all the ports of the switches
    def loop_configure_meraki(port_dict,Downlink_list,switch_name):
        
        ## Configure the switch_name in the Dashboard
        blurb = "This was a conversion from a Catalyst IOSXE config."
        n = 0
        if switch_name == "":
            switch_name = "Switch"
        if len(sw_list) == 1:
            try:
                response = dashboard.devices.updateDevice(sw_list[n], name=switch_name, notes=blurb)
                urls.append(response['url'])
                if debug:
                    print(f"Dashboard response was: {response}")
            except:
                print(f"Unable to configure name on switch.")
        else:
            while n <= len(sw_list)-1:
                try:
                    response = dashboard.devices.updateDevice(sw_list[n], name=switch_name+'-'+str(n+1), notes=blurb)
                    urls.append(response['url'])
                    if debug:
                        print(f"Dashboard response was: {response}")
                except:
                    print("Can't set the switch name for switch " + switch_name+'-'+str(n+1))
                n +=1
        y = 0
        ## Loop to get all the interfaces in the port_dict
        while y <= len(Downlink_list)-1:
            x = Downlink_list[y]
            m = port_dict[x]
            if debug:
                print("\n----------- "+x+" -----------")
                pprint.pprint(m)
            
            ## Check if the interface mode is configured as Access
            if m['mode'] == "access":
                try:
                    Voice_vlan = 0
                    if not m['voice_Vlan'] == "":
                        Voice_vlan = int(m['voice_Vlan'])
                except:
                    pass
                try:
                    if not m['desc'] == "":
                        description = m["desc"]
                except:
                    m["desc"] = ""
                try:
                    if not m['mac'] == []:
                        pass
                except:
                    pass
                try:
                    if not m['data_Vlan'] == "":
                        data_vlan = int(m['data_Vlan'])
                except:
                    data_vlan = 1
                try:
                    if not m['Port_Sec'] == "":
                        mac_limit = m['Port_Sec']
                except:
                    m['Port_Sec'] = ""
            
            ## Check the switch that mapped to those catalyst ports
                sw = int(m['sw_module'])
                if not sw == 0:
                    sw -=1
                if debug:
                    print("Switch Serial Number "+sw_list[sw])
            
            ## Test if the interface has Port security configured or not then apply the right Meraki configuration
                if debug:
                    print(f"Port_Sec = {m['Port_Sec']}")
                if m['Port_Sec'] == "":
                    if debug:
                        print(f"sw = {sw}")
                        print(f"sw_list[sw] = {sw_list[sw]}")
                        print(f"port = {m['port']}")
                        print(f"name = {description}")
                        print(f"enabled = True")
                        print(f"type = access")
                        print(f"vlan = {data_vlan}")
                        print(f"tags = []")
                        print(f"poeEnabled = True")
                        print(f"isolationEnabled = False")
                        print(f"rstpEnabled = True")
                        print(f"stpGuard = disabled")
                        print(f"linkNegotiation = Auto negotiate")
                        print(f"accessPolicyType = Open")
                    try:
                        response = dashboard.switch.updateDeviceSwitchPort(
                            sw_list[sw],
                            m['port'],
                            name=description,
                            enabled=True,
                            type='access',
                            vlan=data_vlan,
                            tags=[],
                            poeEnabled=True,
                            isolationEnabled=False,
                            rstpEnabled=True,
                            stpGuard='disabled',
                            linkNegotiation='Auto negotiate',
                            accessPolicyType='Open'
                        )
                        configured_ports[sw].append(m['port'])
                        if debug:
                            print(f"Dashboard response was: {response}")
                        if not Voice_vlan == 0:
                            if debug:
                                print(f"Setting voice vlan to {Voice_vlan}")
                            try:
                                response = dashboard.switch.updateDeviceSwitchPort(
                                    sw_list[sw],
                                    m['port'],
                                    voiceVlan=Voice_vlan
                                )
                                if debug:
                                    print(f"Dashboard response was: {response}")
                            except:
                                pass
                    except:
                        unconfigured_ports[sw].append(m['port'])
                else:
                    if debug:
                        print(f"sw = {sw}")
                        print(f"sw_list[sw] = {sw_list[sw]}")
                        print(f"port = {m['port']}")
                        print(f"name = {description}")
                        print(f"type = access")
                        print(f"vlan = {data_vlan}")
                        print(f"stickyMacAllowList = {json.dumps(m['mac'])}"),
                        print(f"stickyMacAllowListLimit = {mac_limit}"),
                        print(f"tags = []")
                        print(f"poeEnabled = True")
                        print(f"isolationEnabled = False")
                        print(f"rstpEnabled = True")
                        print(f"stpGuard = disabled")
                        print(f"linkNegotiation = Auto negotiate")
                        print(f"accessPolicyType = Open")
                    try:                       
                        response = dashboard.switch.updateDeviceSwitchPort(
                            sw_list[sw],
                            m['port'],
                            name=description,
                            enabled=True,
                            type='access',
                            vlan=data_vlan,
                            stickyMacAllowList=json.dumps(m['mac']),
                            stickyMacAllowListLimit=mac_limit,
                            tags=[],
                            poeEnabled=True,
                            isolationEnabled=False,
                            rstpEnabled=True,
                            stpGuard='disabled',
                            linkNegotiation='Auto negotiate',
                            accessPolicyType='Open'
                        )
                        configured_ports[sw].append(m['port'])
                        if debug:
                            print(f"Dashboard response was: {response}")
                        if not Voice_vlan == 0:
                            if debug:
                                print(f"Setting voice vlan to {Voice_vlan}")
                            try:
                                response = dashboard.switch.updateDeviceSwitchPort(
                                    sw_list[sw],
                                    m['port'],
                                    voiceVlan=Voice_vlan
                                )
                                if debug:
                                    print(f"Dashboard response was: {response}")
                            except:
                                pass
                    except:
                        unconfigured_ports[sw].append(m['port'])
            ## Check if the interface mode is configured as Trunk
            else:
                description = ""
                try:
                    if not m['desc'] == "":
                        description = m["desc"]
                except:
                    m["desc"] = ""
                    description = m["desc"]
                try:
                    if not m['native'] == "":
                        native_vlan = int(m['native'])
                    else:
                        native_vlan = 1
                except:
                    native_vlan = 1
                    m['native'] = "1"
                try:
                    if not m['trunk_allowed'] == "":
                        trunk_allow = m['trunk_allowed']
                    else:
                        trunk_allow = "1-1000"
                except:
                    m['trunk_allowed'] = "1-1000"
                    trunk_allow = "1-1000"
            
            ## Check the switch that mapped to those catalyst ports
                sw = int(m['sw_module'])
                if not sw == 0:
                    sw -=1
                if debug:
                    print("Switch Serial Number "+sw_list[sw])
                    print(f"sw = {sw}")
                    print(f"sw_list[{sw}] = {sw_list[sw]}")
                    print(f"port = {m['port']}")
                    print(f"name = {description}")
                    print(f"type = trunk")
                    print(f"vlan = {native_vlan}")
                    print(f"allowedVlans= {trunk_allow}")
                    print(f"tags = []")
                    print(f"poeEnabled = True")
                    print(f"isolationEnabled = False")
                    print(f"rstpEnabled = True")
                    print(f"stpGuard = disabled")
                    print(f"linkNegotiation = Auto negotiate")
                    print(f"accessPolicyType = Open")
                try:
                    response = dashboard.switch.updateDeviceSwitchPort(
                        sw_list[sw],
                        m['port'],
                        name=description,
                        enabled=True,
                        type='trunk',
                        vlan=native_vlan,
                        allowedVlans=trunk_allow,
                        tags=[],
                        isolationEnabled=False,
                        rstpEnabled=True,
                        stpGuard='disabled',
                        linkNegotiation='Auto negotiate',
                        accessPolicyType='Open'
                    )
                    configured_ports[sw].append(m['port'])
                    if debug:
                        print(f"Dashboard response was: {response}")
                except:
                    unconfigured_ports[sw].append(m['port'])
                    print("Error in configuring Trunk port "+x)
            if m["active"] == "false":
                try:
                    response = dashboard.switch.updateDeviceSwitchPort(
                        sw_list[sw],
                        m['port'],
                        enabled=False
                    )
                    configured_ports[sw].append(m['port'])
                    if debug:
                        print(f"Dashboard response was: {response}")
                except:
                    unconfigured_ports[sw].append(m['port'])                            
                    print("Error in configuring disabled port "+m)
            else:
                pass
            y +=1
    
    loop_configure_meraki(port_dict,Downlink_list,switch_name)
    return configured_ports,unconfigured_ports,urls

def Meraki_config_up(dashboard,sw_list,port_dict,Uplink_list,nm_list):
    
    debug = DEBUG or DEBUG_TRANSLATOR
    
    configured_ports = defaultdict(list)
    unconfigured_ports = defaultdict(list)
    urls = list()
    
    
    ## Loop to go through all the ports of the switches
    def loop_configure_meraki(port_dict,Uplink_list,switch_name):
        
        ## Loop to get all the interfaces in the port_dict
        y = 0
        while y <= len(Uplink_list)-1:
            x = Uplink_list[y]
            m = port_dict[x]
            if debug:
                print("\n----------- "+x+" -----------")
                pprint.pprint(m)
            
            ## Check if the interface mode is configured as Access
            if m['mode'] == "access":
                try:
                    Voice_vlan = 0
                    if not m['voice_Vlan'] == "":
                        Voice_vlan = int(m['voice_Vlan'])
                except:
                    pass
                try:
                    if not m['desc'] == "":
                        description = m["desc"]
                except:
                    m["desc"] = ""
                try:
                    if not m['mac'] == []:
                        pass
                except:
                    pass
                try:
                    if not m['data_Vlan'] == "":
                        data_vlan = int(m['data_Vlan'])
                except:
                    data_vlan = 1
                try:
                    if not m['Port_Sec'] == "":
                        mac_limit = m['Port_Sec']
                except:
                    m['Port_Sec'] = ""
            
            ## Check the switch that mapped to those catalyst ports
                sw = int(m['sw_module'])
                if not sw == 0:
                    sw -=1
                if debug:
                    print("Switch Serial Number "+sw_list[sw])
            
            ## Test if the interface has Port security configured or not then apply the right Meraki configuration
                if debug:
                    print(f"Port_Sec = {m['Port_Sec']}")
                if m['Port_Sec'] == "":
                    if debug:
                        print(f"sw = {sw}")
                        print(f"sw_list[sw] = {sw_list[sw]}")
                        print(f"port = {m['port']}")
                        print(f"name = {description}")
                        print(f"enabled = True")
                        print(f"type = access")
                        print(f"vlan = {data_vlan}")
                        print(f"tags = []")
                        print(f"poeEnabled = True")
                        print(f"isolationEnabled = False")
                        print(f"rstpEnabled = True")
                        print(f"stpGuard = disabled")
                        print(f"linkNegotiation = Auto negotiate")
                        print(f"accessPolicyType = Open")
                    try:
                        response = dashboard.switch.updateDeviceSwitchPort(
                            sw_list[sw],
                            m['port'],
                            name=description,
                            enabled=True,
                            type='access',
                            vlan=data_vlan,
                            tags=[],
                            poeEnabled=True,
                            isolationEnabled=False,
                            rstpEnabled=True,
                            stpGuard='disabled',
                            linkNegotiation='Auto negotiate',
                            accessPolicyType='Open'
                        )
                        configured_ports[sw].append(m['port'])
                        if debug:
                            print(f"Dashboard response was: {response}")
                        if not Voice_vlan == 0:
                            if debug:
                                print(f"Setting voice vlan to {Voice_vlan}")
                            try:
                                response = dashboard.switch.updateDeviceSwitchPort(
                                    sw_list[sw],
                                    m['port'],
                                    voiceVlan=Voice_vlan
                                )
                                if debug:
                                    print(f"Dashboard response was: {response}")
                            except:
                                pass
                    except:
                        unconfigured_ports[sw].append(m['port'])
                else:
                    if debug:
                        print(f"sw = {sw}")
                        print(f"sw_list[sw] = {sw_list[sw]}")
                        print(f"port = {m['port']}")
                        print(f"name = {description}")
                        print(f"type = access")
                        print(f"vlan = {data_vlan}")
                        print(f"stickyMacAllowList = {json.dumps(m['mac'])}"),
                        print(f"stickyMacAllowListLimit = {mac_limit}"),
                        print(f"tags = []")
                        print(f"poeEnabled = True")
                        print(f"isolationEnabled = False")
                        print(f"rstpEnabled = True")
                        print(f"stpGuard = disabled")
                        print(f"linkNegotiation = Auto negotiate")
                        print(f"accessPolicyType = Open")
                    try:                       
                        response = dashboard.switch.updateDeviceSwitchPort(
                            sw_list[sw],
                            m['port'],
                            name=description,
                            enabled=True,
                            type='access',
                            vlan=data_vlan,
                            stickyMacAllowList=json.dumps(m['mac']),
                            stickyMacAllowListLimit=mac_limit,
                            tags=[],
                            poeEnabled=True,
                            isolationEnabled=False,
                            rstpEnabled=True,
                            stpGuard='disabled',
                            linkNegotiation='Auto negotiate',
                            accessPolicyType='Open'
                        )
                        configured_ports[sw].append(m['port'])
                        if debug:
                            print(f"Dashboard response was: {response}")
                        if not Voice_vlan == 0:
                            if debug:
                                print(f"Setting voice vlan to {Voice_vlan}")
                            try:
                                response = dashboard.switch.updateDeviceSwitchPort(
                                    sw_list[sw],
                                    m['port'],
                                    voiceVlan=Voice_vlan
                                )
                                if debug:
                                    print(f"Dashboard response was: {response}")
                            except:
                                pass
                    except:
                        unconfigured_ports[sw].append(m['port'])
            ## Check if the interface mode is configured as Trunk
            else:
                description = ""
                try:
                    if not m['desc'] == "":
                        description = m["desc"]
                except:
                    m["desc"] = ""
                    description = m["desc"]
                try:
                    if not m['native'] == "":
                        native_vlan = int(m['native'])
                    else:
                        native_vlan = 1
                except:
                    native_vlan = 1
                    m['native'] = "1"
                try:
                    if not m['trunk_allowed'] == "":
                        trunk_allow = m['trunk_allowed']
                    else:
                        trunk_allow = "1-1000"
                except:
                    m['trunk_allowed'] = "1-1000"
                    trunk_allow = "1-1000"
            
            ## Check the switch that mapped to those catalyst ports
                sw = int(m['sw_module'])
                if not sw == 0:
                    sw -=1
                if debug:
                    print("Switch Serial Number "+sw_list[sw])
                    print(f"sw = {sw}")
                    print(f"sw_list[{sw}] = {sw_list[sw]}")
                    print(f"port = {m['port']}")
                    print(f"name = {description}")
                    print(f"type = trunk")
                    print(f"vlan = {native_vlan}")
                    print(f"allowedVlans= {trunk_allow}")
                    print(f"tags = []")
                    print(f"poeEnabled = True")
                    print(f"isolationEnabled = False")
                    print(f"rstpEnabled = True")
                    print(f"stpGuard = disabled")
                    print(f"linkNegotiation = Auto negotiate")
                    print(f"accessPolicyType = Open")
                try:
                    response = dashboard.switch.updateDeviceSwitchPort(
                        sw_list[sw],
                        m['port'],
                        name=description,
                        enabled=True,
                        type='trunk',
                        vlan=native_vlan,
                        allowedVlans=trunk_allow,
                        tags=[],
                        isolationEnabled=False,
                        rstpEnabled=True,
                        stpGuard='disabled',
                        linkNegotiation='Auto negotiate',
                        accessPolicyType='Open'
                    )
                    configured_ports[sw].append(m['port'])
                    if debug:
                        print(f"Dashboard response was: {response}")
                except:
                    unconfigured_ports[sw].append(m['port'])
                    print("Error in configuring Trunk port "+x)
            if m["active"] == "false":
                try:
                    response = dashboard.switch.updateDeviceSwitchPort(
                        sw_list[sw],
                        m['port'],
                        enabled=False
                    )
                    configured_ports[sw].append(m['port'])
                    if debug:
                        print(f"Dashboard response was: {response}")
                except:
                    unconfigured_ports[sw].append(m['port'])                            
                    print("Error in configuring disabled port "+m)
            else:
                pass
            y +=1
    
    loop_configure_meraki(port_dict,Uplink_list,switch_name)
    return configured_ports,unconfigured_ports,urls
