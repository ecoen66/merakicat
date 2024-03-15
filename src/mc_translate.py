import meraki
import batch_helper
from ciscoconfparse2 import CiscoConfParse
from collections import defaultdict
import ipaddress
import os, requests, json, pprint, re
from mc_user_info import *
from mc_pedia import *

def Evaluate(config_file):
    """
    This parent function will evaluate a Catalyst switch config file and reports on
    which features that are being used can and cannot be mapped to Meraki features.
    :param config_file: The catalyst IOSXE config file to parse through
    :return: Lists of uplinks, downlinks and other ports as well as 
    :      : a dictionary with all of the ports and their settings, and the hostname
    """

    debug = DEBUG or DEBUG_TRANSLATOR
    
    port_dict = {}
    switch_dict = {}
    ## List of interfaces that are shut
    shut_interfaces = list()
    def read_Cisco_SW():
        """
        This sub-function parses the Catalyst switch config file and report on which
        features that are being used can and cannot be mapped to Meraki features.
        :param NONE: Using global variables in the parent function
        :return: Lists of uplinks, downlinks and other ports as well as 
        :      : a dictionary with all of the ports and their settings, and the hostname
        """
        for key,val in mc_pedia['switch'].items():
            switch_dict[key] = ""
        if debug:
            print(f"switch_dict = {switch_dict}")
        ##Parsing the Cisco Catalyst configuration (focused on the interface config)
        if debug:
            print("-------- Reading <"+config_file+"> Configuration --------")
        parse = CiscoConfParse(config_file, syntax='ios', factory=True)
        
        ###
        ###
        ### Try out our mc_pedia for the switch name
        for key,val in mc_pedia['switch'].items():
            newvals = {}
            exec(val.get('iosxe'),locals(),newvals)
            switch_dict[key] = newvals[key]
            if debug:
                print(f"switch_dict['{key}'] = {switch_dict[key]}")
        '''
        switch_name_obj = parse.find_objects('^hostname')
        if not switch_name_obj == []:
            switch_name = switch_name_obj[0].re_match_typed('^hostname\s(\S+)')
        '''
        Gig_uplink= list()
        Ten_Gig_uplink= list()
        Twenty_Five_Gig_uplink= list()
        Forty_Gig_uplink= list()
        Hundred_Gig_uplink= list()
        All_interfaces= defaultdict(list)
        
        # Grab all shutdown interfaces
        intf_for_test = parse.find_parent_objects([r'^interface', r'^\s+shutdown'])
        ## Remove the management, Loopback, Port-channel and VLAN interfaces from
        ## the intf_for_test list
        intf_for_test[:] = [y for y in intf_for_test if not (
            y.re_match_typed('^interface\s+(\S.*)$') == "GigabitEthernet0/0" or
            y.re_match_typed('^interface\s+(\S.*)$').startswith("Loopback") or
            #y.re_match_typed('^interface\s+(\S.*)$').startswith("Vlan") or
            #y.re_match_typed('^interface\s+(\S.*)$').startswith("Port-channel") or
            y.re_match_typed('^interface\s+(\S.*)$').startswith("AppGig"))]
        ## Test the remaining interfaces for shutdown and add to shut list
        for intf_obj in intf_for_test:
            shut_interfaces.append(intf_obj.re_match_typed('^interface\s+(\S.+?)$'))
##        print(f"These are the shut interfaces: {shut_interfaces}")
        
        ## Select all interfaces
        intf = parse.find_objects('^interface')
        if debug:
            print(f"intf = {intf}")
        ## Remove the management, Loopback, Port-channel and VLAN interfaces from
        ## the interface list
        intf[:] = [x for x in intf if not (
            x.re_match_typed('^interface\s+(\S.*)$') == "GigabitEthernet0/0" or
            x.re_match_typed('^interface\s+(\S.*)$').startswith("Loopback") or
            #x.re_match_typed('^interface\s+(\S.*)$').startswith("Vlan") or
            #x.re_match_typed('^interface\s+(\S.*)$').startswith("Port-channel") or
            x.re_match_typed('^interface\s+(\S.*)$').startswith("AppGig"))]
        
        
        for intf_obj in intf:
            ## Get the interface name
            intf_name = intf_obj.re_match_typed('^interface\s+(\S.*)$')
            
            #Only interface name will be used to catogrize different types of interfaces (downlink and uplink)
            only_intf_name = re.sub("\d+|\\/","",intf_name)
            if not only_intf_name == "Vlan":
                if only_intf_name == "Port-channel":
                    Switch_module = "0"
                else:
                    Switch_module = intf_obj.re_match_typed('^interface\s\S+?thernet+(\d)')
                    if Switch_module == "":
                        Switch_module = intf_obj.re_match_typed('^interface\s\S+?GigE+(\d)')
                
                All_interfaces[only_intf_name].append(intf_name)
                
                port_dict[intf_name] = {}
                port_dict[intf_name]['sw_module'] = "1"
                port_dict[intf_name]['sub_module'] = "0"
                #port_dict[intf_name]['desc'] = ""
                port_dict[intf_name]['port'] = ""
                #[intf_name]['mode'] = ""
                port_dict[intf_name]['mac'] = []
                port_dict[intf_name]['active'] = "true"
                #try:
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
                if Switch_module == "0":
                    port_dict[intf_name]['sw_module'] = "1"
                if not Switch_module == "" and not Switch_module == "0":
                    port_dict[intf_name]['sw_module'] = Switch_module
                
                port_dict[intf_name]['port'] = port
                port_dict[intf_name]['mac'].clear()
                ## check if the interface in the shutdown list then mark it as shutdown
                if intf_name in shut_interfaces:
                    port_dict[intf_name]['active'] = "false"
                
            else:
                # interface Vlan#
                All_interfaces[only_intf_name].append(intf_name)
                port_dict[intf_name] = {}
                port_dict[intf_name]['active'] = "true"
                port_dict[intf_name]['vlan'] = intf_obj.re_match_typed('^interface\sVlan(\d+)')
                print(f"for {intf_name}, vlan is {port_dict[intf_name]['vlan']}")
            
            if debug:
                print("Checking children")
            int_fx = intf_obj.children
            if debug:
                print(f"Children are: {int_fx}")
            
            ## Capture the configuration of the interface
            port_sec_raw = max_mac = ""
            for child in int_fx:
                ### Try out our mc_pedia
                if debug:
                    print(f"child = {child}")
                for key,val in mc_pedia['port'].items():
                    newvals = {}
                    if debug:
                        print(f"key,val = {key},{val}")
                    if not val['regex'] == "":
                        if not child.re_match_typed(regex=val['regex']) == "":
                            if not val['iosxe'] == "":
                                exec(val.get('iosxe'),locals(),newvals)
                                if debug:
                                    print(f"newvals[{key}] = {newvals[key]}")
                                if not newvals[key] == "":
                                    port_dict[intf_name][key] = newvals[key]
                try:
                    port_sec_raw = child.re_match_typed(regex=r'\sswitchport\sport-security\smac-address\ssticky\s+(\S.+)')
                except:
                    pass
                #try:
                #    port_channel = child.re_match_typed(regex=r'\schannel-group\s+(\d)')
                #except:
                #    pass
                try:
                    max_mac = child.re_match_typed(regex=r'\sswitchport\sport-security\smaximum\s+(\d)')
                except:
                    pass
                if not port_sec_raw == "":
                    port_dict[intf_name]['mac'].append(mac_build(port_sec_raw))
                #if not port_channel == "":
                #    port_dict[intf_name]['LACP_Group'] = port_channel
                if not max_mac == "":
                    port_dict[intf_name]['Port_Sec'] = max_mac
        
        Uplink_list, Downlink_list, Other_list = split_down_up_link(All_interfaces,Gig_uplink)
        if debug:
            print(f"Uplink_list = {Uplink_list}\n")
            print(f"Downlink_list = {Downlink_list}\n")
            print(f"Other_list = {Other_list}\n")
            print(f"port_dict = {port_dict}\n")
            print(f"switch_dict = {switch_dict}\n")
        return Uplink_list, Downlink_list, Other_list, port_dict, switch_dict
    
    def split_down_up_link(interfaces_list, Gig_uplink):
        """
        This sub-function takes a list of interfaces and sorts them into uplinks,
        downlinks and others.
        :param interfaces_list: The dictlist of interfaces categorized by type (i.e.:GigabitEthernet) 
        :param Gig_uplink: 
        :return: Lists of uplinks, downlinks and other ports
        """
        Uplink_list=list()
        Downlink_list=list()
        Other_list =list()
        
        #Creating a copy of the interface list to avoid Runtime error
        interfaces_list_copy = interfaces_list.copy()
        if debug:
            print(f"interfaces_list = {interfaces_list}\n")
        for key, value in interfaces_list.items():
        #Layer 3 ports always considered as downlinks
            if key == "Vlan":
                for value in interfaces_list_copy["Vlan"]:
                    Downlink_list.append(value)
        #HundredGigabitEthernet ports always considered as uplinks
            if key == "HundredGigabitEthernet":
                for value in interfaces_list_copy["HundredGigabitEthernet"]:
                    Uplink_list.append(value)
        #FortyGigbitEthernet ports always considered as uplinks
            if key == "FortyGigabitEthernet":
                for value in interfaces_list_copy["FortyGigabitEthernet"]:
                    Uplink_list.append(value)
        #TwentyFiveGigbitEthernet ports always considered as uplinks
            if key == "TwentyFiveGigE":
                for value in interfaces_list_copy["TwentyFiveGigE"]:
                    Uplink_list.append(value)
        #TengigbitEthernet ports always considered as uplinks
            if key == "TenGigabitEthernet":
                for value in interfaces_list_copy["TenGigabitEthernet"]:
                    Uplink_list.append(value)
        #GigbitEthernet ports to be evaluated if it has 1 in subnetwork module (x/1/x)
        # then its uplink otherwise will be downlink
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
                        key=="GigabitEthernet" or key=="FastEthernet" or \
                        key=="Vlan":
                        pass
                    else:
                        Other_list.append(value)
        return Uplink_list, Downlink_list, Other_list
    
    ## rebuild the mac address to match Meraki format
    def mac_build(my_str, group=2, char=':'):
        """
        This sub-function takes an IOSXE MAC address and reformats it into the Meraki
        format.
        :param my_str: The MAC address from IOSXE 
        :param group: How many digits to group between delimiters (2 = :00:)
        :param char: The delimiter to use between digit groupings
        :return: A string containing the translate MAC address
        """
        port_sec = re.findall(re.compile(r'[a-fA-F0-9.]{14}'), my_str)[0]
        p = re.compile(r'^[a-fA-F0-9.]{14}')
        new_p = re.sub("\.","",port_sec)
        my_str = str(new_p)
        
        last = char.join(my_str[i:i+group] for i in range(0, len(my_str), group))
        return last
    
    ## Extract out the details of the switch module and the port number
    def check(intf):
        """
        This sub-function takes an IOSXE long interface name and splits it into
        a submodule and a port.
        :param intf: An IOSXE long interface name
        :return: A string with the submodule number and one with the port number
        """
        if debug:
            print(f"Checking interface {intf}.")
       # intf_rgx = re.compile(r'^interface GigabitEthernet(\d+)\/(\d+)\/(\d+)$')
        obj = re.search(r'(?:Ethernet|GigE|channel)(\d+)\/(\d+)\/(\d+)$',intf)
        if not obj == None:
            if debug:
                print(f"obj.group(0) = {obj.group(0)}")
                print(f"obj.group(1) = {obj.group(1)}")
                print(f"obj.group(2) = {obj.group(2)}")
                print(f"obj.group(3) = {obj.group(3)}")
            port = obj.group(3)
            Sub_module = obj.group(2)
        else:
            obj = re.search(r'(?:channel)(\d+)$',intf)
            if debug:
                print(f"obj.group(0) = {obj.group(0)}")
                print(f"obj.group(1) = {obj.group(1)}")
            port = obj.group(1)
            Sub_module = 0
        return port,Sub_module
    
    Uplink_list, Downlink_list, Other_list, port_dict, switch_name  = read_Cisco_SW()
    print(f"\nDownlink_list = {Downlink_list}")
    print(f"\nOther_list = {Other_list}")
    print(f"\nUplink_list = {Uplink_list}")
    return Uplink_list, Downlink_list, Other_list, port_dict, switch_dict


def Meraki_config_down(dashboard,organization_id,switch_path,sw_list,port_dict,Downlink_list,Other_list,switch_dict):
    """
    This parent function will convert Catalyst switch config features to Meraki features
    and send them to Dashboard to program Meraki switches.
    :param dashboard: The active Meraki dashboard API session to use
    :param organization_id: The Meraki Organization ID used in batch configuration
    :param sw_list: The list of Meraki switch serial numbers to configure
    :param port_dict: The dictionary of IOSXE ports and features from the Evaluate function
    :param Downlink_list: The list of ports to configure
    :param switch_name: The catalyst IOSXE hostname 
    :return: Lists of configured and unconfigured ports, and a list with a URL to each
    :      : of the Meraki switches that we configured or modified
    """
    
    debug = DEBUG or DEBUG_TRANSLATOR
    
    # create a batch action lists
    action_list = list()
    all_actions = list()
    returns_dict = {}
    post_ports_list = list()
    # create good and bad port lists 
    configured_ports = defaultdict(list)
    unconfigured_ports = defaultdict(list)
    
    if debug:
        print(f"Other_list = {Other_list}")
        for port in Other_list:
            if port in port_dict.keys():
                print(f"port_dict['{port}'] = {port_dict[port]}")
    
    # create a place to hold all of the arguments to send to Dashboard
    # to update a switch port
    args = list(dict())
    
    ## Loop to go through all the ports of the switches
    def loop_configure_meraki(port_dict,Downlink_list,switch_dict):
        """
        This sub-function does the actual work of setting the meraki functions based on the
        dictionary of IOSXE ports and features from the Evaluate function.
        :param port_dict: The dictionary of IOSXE ports and features from the Evaluate function
        :param Downlink_list: The list of ports to configure
        :param switch_name: The catalyst IOSXE hostname 
        :return: NONE - modifies global variables in the parent function
        """
        
        
        # create a place to hold the Dashboard URL for each switch
        ## Configure the switch_name in the Dashboard
        if debug:
            print(f"switch_dict = {switch_dict}")
        for key,val in mc_pedia['switch'].items():
            if (val['translatable'] == "✓" and val['meraki']['skip'] == "post_process") or val['meraki']['skip'] == "post_ports":
                if val['meraki']['skip'] == "post_ports":
                    post_ports_list.append([key, True])
                newvals = {}
                exec(val['meraki'].get('post_process'),locals(),newvals)
                if debug:
                    print(f"newvals = {newvals}")
                return_vals = newvals['return_vals']
                if debug:
                    print(f"newvals['return_vals'] = {newvals['return_vals']}")
                n = 0
                while n < len(return_vals):
                    returns_dict[return_vals[n]] = switch_dict[return_vals[n]] = newvals[return_vals[n]]
                    n += 1
                if debug:
                    print(f"switch_dict = {switch_dict}")
                
        ## Loop to get all the interfaces in the port_dict
        y = 0
        while y <= len(Downlink_list)-1:
            interface_descriptor = Downlink_list[y]
            interface_settings = port_dict[interface_descriptor]
            if debug:
                print("\n----------- "+interface_descriptor+" -----------")
                pprint.pprint(interface_settings)
            
            ## Check the switch that mapped to those catalyst ports
            try:
                switch_num = int(interface_settings['sw_module'])
            except:
                switch_num = 1
            if not switch_num == 0:
                switch_num -=1
            
            
            if not 'Vlan' in interface_descriptor:
                args.append([sw_list[switch_num],interface_settings['port'],{}])
                args[y][2].update({'enabled':True,
                    'tags':[],
                    'poeEnabled':True,
                    'isolationEnable':False,
                    'rstpEnabled':True,
                    'accessPolicyType':'Open'})
                for key,val in mc_pedia['port'].items():
                    newvals = {}
                    if not val['meraki']['skip'] == True:
                        if val['meraki']['skip'] in ['post_process','post_ports']:
                            exec(val['meraki'].get('post_process'),locals(),newvals)
                            if debug:
                                print(f"newvals = {newvals}")
                            if val['meraki']['skip'] == 'post_process':
                                if not newvals[key] == "":
                                    interface_settings[key] = newvals[key]
                        try:
                            args[y][2].update({key: interface_settings[key]})
                        except:
                            if "default" in val['meraki']:
                                interface_settings[key] = val['meraki']['default']
                                args[y][2].update({key: interface_settings[key]})
                        if "return_vals" in newvals:
                            return_vals = newvals['return_vals']
                            if debug:
                                print(f"newvals['return_vals'] = {newvals['return_vals']}")
                            n = 0
                            while n < len(return_vals):
                                if debug:
                                    print(f"return_vals[{n}] = {return_vals[n]}")
                                    print(f"post_ports_list = {post_ports_list}")
                                post_ports_list.append([return_vals[n],newvals[return_vals[n]]])
                                if debug:
                                    print(f"post_ports_list = {post_ports_list}")
                                n += 1
                try:
                    args[y][2].update({'enabled':False if interface_settings["active"] == "false" else True})
                except:
                    pass
                ## Check if the interface mode is configured as Access
                if interface_settings['type'] == "access":
                    try:
                        if not interface_settings['mac'] == []:
                            pass
                    except:
                        pass
                    try:
                        if not interface_settings['Port_Sec'] == "":
                            mac_limit = interface_settings['Port_Sec']
                    except:
                        interface_settings['Port_Sec'] = ""
                    if not interface_settings['Port_Sec'] == "":
                        args[y][2].update({'accessPolicyType':'Sticky MAC allow list',
                            'stickyMacAllowList':json.dumps(interface_settings['mac']),
                            'stickyMacAllowListLimit':mac_limit})
            
            else:
                args.append([returns_dict['networkId'],returns_dict['switchStackId'],interface_descriptor,interface_settings['vlan'],{}])
                for key,val in mc_pedia['layer3'].items():
                    newvals = {}
                    if not val['meraki']['skip'] == True:
                        if val['meraki']['skip'] in ['post_process','post_ports']:
                            exec(val['meraki'].get('post_process'),locals(),newvals)
                            if debug:
                                print(f"newvals = {newvals}")
                            if val['meraki']['skip'] == 'post_process':
                                if not newvals[key] == "":
                                    interface_settings[key] = newvals[key]
                        if debug:
                            print(f"key = {key}, newvals[key] = {newvals[key]}")
                        try:
                            args[y][4].update({key: interface_settings[key]})
                        except:
                            if "default" in val['meraki']:
                                interface_settings[key] = val['meraki']['default']
                                args[y][4].update({key: interface_settings[key]})
                        if "return_vals" in newvals:
                            return_vals = newvals['return_vals']
                            if debug:
                                print(f"newvals['return_vals'] = {newvals['return_vals']}")
                            n = 0
                            while n < len(return_vals):
                                if debug:
                                    print(f"return_vals[{n}] = {return_vals[n]}")
                                    print(f"post_ports_list = {post_ports_list}")
                                args[y][4].update({return_vals[n]: newvals[return_vals[n]]})
                                if debug:
                                    print(f"args for {interface_descriptor} = {args[y][4]}")
                                n += 1
                if debug:
                    print(f"args[{y}] = {args[y]}")
            ## Append args to the port_dict as meraki_args
            port_dict[interface_descriptor]['meraki_args'] = args[y]
            
            ## Append the port update call to Dashboard to the batch list
            if debug:
                print(f"Number of sub lists in action_list is {len(action_list)}")
                try:
                    print(f"Number of batch actions in action_list[{switch_num}] is {len(action_list[switch_num])}")
                except:
                    pass
                #print(f"About to append action for port {interface_settings['port']}")
            
            if not len(action_list) == switch_num+1:
                # We are on to the next switch, so I want a new sublist
                action_list.append([])
            # Add this action to the action_list sublist for the switch
            if not 'Vlan' in interface_descriptor:
                try:
                    action_list[switch_num].append(dashboard.batch.switch.updateDeviceSwitchPort(
                    args[y][0],
                    args[y][1],
                    **args[y][2]
                    ))
                except:
                    unconfigured_ports[switch_num].append(interface_settings['port'])
                    print(f"We caught an exception configuring {interface_settings['port']} on {switch_num}")
                if not interface_settings['port'] in unconfigured_ports[switch_num]:
                    configured_ports[switch_num].append(interface_settings['port'])
            y +=1
        
        ## post_ports processing
        if debug:
            print(f"At post_ports, port_dict = {port_dict}")
            print(f"Length of post_ports_list = {len(post_ports_list)}")
            print(f"post_ports_list = {post_ports_list}")
        if not len(post_ports_list) == 0:
            short_list = list(set(map(lambda x: x[0], post_ports_list)))
            if debug:
                print(f"short_list = {short_list}")

            # This is the processing loop for port-level post ports processes
            item = 0
            while item < len(short_list):
                if debug:
                    print(f"short_list[{item}] = {short_list[item]}")
                # Call the post-post process for that feature
                newvals = {}
                if short_list[item] in mc_pedia['port'].keys():
                    exec(mc_pedia['port'][short_list[item]]['meraki'].get('post_ports_process'),locals(),newvals)
                    if "return_vals" in newvals:
                        return_vals = newvals['return_vals']
                        if "channel_port_dict" in return_vals:
                            if debug:
                                print(f"newvals['channel_port_dict'] = {newvals['channel_port_dict']}")
                            for a_port in newvals['channel_port_dict']:
                                if debug:
                                    print(f"a_port = {a_port}")
                                port_dict[a_port] = newvals['channel_port_dict'][a_port]
                                if debug:
                                    print(f"port_dict[a_port] = {port_dict[a_port]}")
                        if 'configured_ports' in return_vals:
                            cp_list = newvals['configured_ports']
                            if debug:
                                print(f"cp_list = {cp_list}")
                            for port in cp_list:
                                switch_num = "stack" if len(sw_list) > 1 else 1
                                configured_ports[switch_num].append(port) 
                        if 'unconfigured_ports' in return_vals:
                            up_list = newvals['unconfigured_ports']
                            if debug:
                                print(f"up_list = {up_list}")
                            for port in up_list:
                                switch_num = "stack" if len(sw_list) > 1 else 1
                                unconfigured_ports[switch_num].append(port) 
                item += 1
            
            # This is not used yet, but I left this here in case we need it later for
            # switch-level post ports processes
            item = 0
            while item < len(short_list):
                if debug:
                    print(f"short_list[{item}] = {short_list[item]}")
                # Call the post-post process for that feature
                newvals = {}
                if short_list[item] in mc_pedia['switch'].keys():
                    exec(mc_pedia['switch'][short_list[item]]['meraki'].get('post_ports_process'),locals(),newvals)
                    print(f"return_vals = {return_vals}")
                    if "return_vals" in newvals:
                        return_vals = newvals['return_vals']
                        pass
                item += 1
        
        if debug:
            print(f"\n\naction_list = {action_list}\n\n")
    loop_configure_meraki(port_dict,Downlink_list,switch_dict)
    
    # Combine all of the action_list sublists into a larger set for batching
    x = 0
    while x <= len(action_list)-1:
       all_actions.extend(action_list[x])
       x += 1
    if debug:
        print(f"all_actions = {all_actions}")
    
    # Save an action batch file for the port features
    #dir = os.path.join(os.getcwd(),"../files")
    #with open(os.path.join(dir,switch_path+".ab0"), 'w') as file:
    #    file.write(json.dumps(all_actions)) # use `json.loads` to do the reverse
    #    file.close()
    
    if debug:
        print(f"Number of batch actions for Dashboard: {len(action_list)}\n")
        print(f"Args listdict is: {args}\n")
    
    issues = list()
    test_helper = batch_helper.BatchHelper(dashboard, organization_id, all_actions, linear_new_batches=False, actions_per_new_batch=100)
    test_helper.prepare()
    test_helper.generate_preview()
    test_helper.execute()
    if debug:
        print(f'helper status is {test_helper.status}')
    
    #try:
    batches_report = dashboard.organizations.getOrganizationActionBatches(organization_id)
    #except:
    #    pass
    new_batches_statuses = [{'id': batch['id'], 'status': batch['status']} for batch in batches_report if batch['id'] in test_helper.submitted_new_batches_ids]
    if debug:
        print(f'Batch status returned is: {new_batches_statuses}')
    failed_batch_ids = [batch['id'] for batch in new_batches_statuses if batch['status']['failed']]
    if debug:
        print(f'Failed batch IDs are as follows: {failed_batch_ids}')
        
    if debug:
        print(f"\nport_dict = {port_dict}\n")
    
    return configured_ports,unconfigured_ports,port_dict,returns_dict['urls'],returns_dict['networkId']
'''
def Meraki_config_up(dashboard,organization_id,networkId,sw_list,ToBeConfigured,Uplink_list,nm_list,ChannelsToBeConfigured,Other_list):
    """
    This parent function will convert Catalyst switch uplink port config features to
    Meraki features and send them to Dashboard to program Meraki switches.
    :param dashboard: The active Meraki dashboard API session to use
    :param organization_id: The Meraki Organization ID used in batch configuration
    :param sw_list: The list of Meraki switch serial numbers to configure
    :param port_dict: The dictionary of IOSXE ports and features from the Evaluate function
    :param Uplink_list: The list of ports to configure
    :param nm_list: The list of nm_modules installed per switch
    :param channel_dict: The dictionary of IOSXE port-channels and features from the Evaluate function
    :param Channels_list: The list of port-channels to configure
    :return: Lists of configured and unconfigured ports & channels
    """
    
    debug = DEBUG or DEBUG_TRANSLATOR
    
    configured_ports = defaultdict(list)
    unconfigured_ports = defaultdict(list)
    configured_channels = defaultdict(list)
    unconfigured_channels = defaultdict(list)
    
    ## Loop to go through all the ports of the switches
    def loop_configure_meraki_up(port_dict,Uplink_list):
        
        ## Loop to get all the interfaces in the port_dict
        y = 0
        while y <= len(Other_list)-1:
            interface_descriptor = Other_list[y]
            if not re.search('Port-channel', interface_descriptor) == None:
                interface_settings = port_dict[interface_descriptor]
                if debug:
                    print("\n----------- "+interface_descriptor+" -----------")
                    pprint.pprint(interface_settings)
                args.append([interface_settings['switchPorts'][0]['serial'],[interface_settings['switchPorts'][0]['portId'],{}])
                args[y][2].update({'enabled':interface_settings['active'],
                    'tags':[],
                    'poeEnabled':True,
                    'isolationEnable':False,
                    'rstpEnabled':True,
                    'accessPolicyType':'Open'})
                newvals = {}
                for key,val in mc_pedia['port'].items():
                    newvals = {}
                    if not val['meraki']['skip'] == True:
                        if val['meraki']['skip'] in ['post_process','post_post']:
                            exec(val['meraki'].get('post_process'),locals(),newvals)
                            if debug:
                                print(f"newvals = {newvals}")
                            if val['meraki']['skip'] == 'post_process':
                                if not newvals[key] == "":
                                    interface_settings[key] = newvals[key]
                        try:
                            args[y][2].update({key: interface_settings[key]})
                        except:
                            if "default" in val['meraki']:
                                interface_settings[key] = val['meraki']['default']
                                args[y][2].update({key: interface_settings[key]})
                        if "return_vals" in newvals:
                            return_vals = newvals['return_vals']
                            if debug:
                                print(f"newvals['return_vals'] = {newvals['return_vals']}")
                            n = 0
                            while n < len(return_vals):
                                if debug:
                                    print(f"return_vals[{n}] = {return_vals[n]}")
                                    print(f"post_post_list = {post_post_list}")
                                post_post_list.append([return_vals[n],newvals[return_vals[n]]])
                                if debug:
                                    print(f"post_post_list = {post_post_list}")
                                n += 1
                try:
                    args[y][2].update({'enabled':False if interface_settings["active"] == "false" else True})
                except:
                    pass            
                ## Check if the interface mode is configured as Access
                if interface_settings['type'] == "access":
                    try:
                        if not interface_settings['mac'] == []:
                            pass
                    except:
                        pass
                    try:
                        if not interface_settings['Port_Sec'] == "":
                            mac_limit = interface_settings['Port_Sec']
                    except:
                        interface_settings['Port_Sec'] = ""
                    if not interface_settings['Port_Sec'] == "":
                        args[y][2].update({'accessPolicyType':'Sticky MAC allow list',
                            'stickyMacAllowList':json.dumps(interface_settings['mac']),
                            'stickyMacAllowListLimit':mac_limit})
                
                ## Append the port update call to Dashboard to the batch list
                if debug:
                    print(f"Number of sub lists in action_list is {len(action_list)}")
                    try:
                        print(f"Number of batch actions in action_list[{switch_num}] is {len(action_list[switch_num])}")
                    except:
                        pass
                    print(f"About to append action for port {interface_settings['port']}")
                
                if not len(action_list) == switch_num+1:
                    # We are on to the next switch, so I want a new sublist
                    action_list.append([])
                # Add this action to the action_list sublist for the switch
                try:
                    action_list[switch_num].append(dashboard.batch.switch.updateDeviceSwitchPort(
                    args[y][0],
                    args[y][1],
                    **args[y][2]
                    ))
                except:
                    unconfigured_ports[switch_num].append(interface_settings['port'])
                if not interface_settings['port'] in unconfigured_ports[switch_num]:
                    configured_ports[switch_num].append(interface_settings['port'])
            y +=1
    
    loop_configure_meraki(port_dict,Downlink_list,switch_dict)
    
    # Combine all of the action_list sublists into a larger set for batching
    x = 0
    while x <= len(action_list)-1:
        all_actions.extend(action_list[x])
        x += 1
    
    if debug:
        print(f"Number of batch actions for Dashboard: {len(all_actions)}\n")
        print(f"Args listdict is: {args}\n")
    
    test_helper = batch_helper.BatchHelper(dashboard, organization_id, all_actions, linear_new_batches=False, actions_per_new_batch=100)
    test_helper.prepare()
    test_helper.generate_preview()
    test_helper.execute()
    if debug:
        print(f'helper status is {test_helper.status}')
    
    #try:
    batches_report = dashboard.organizations.getOrganizationActionBatches(organization_id)
    #except:
    #    pass
    new_batches_statuses = [{'id': batch['id'], 'status': batch['status']} for batch in batches_report if batch['id'] in test_helper.submitted_new_batches_ids]
    if debug:
        print(f'Batch status returned is: {new_batches_statuses}')
    failed_batch_ids = [batch['id'] for batch in new_batches_statuses if batch['status']['failed']]
    if debug:
        print(f'Failed batch IDs are as follows: {failed_batch_ids}')
        
        
        
        ## Loop to get all the interfaces in the port_dict
        y = 0
        while y <= len(Uplink_list)-1:
            x = Uplink_list[y]
            m = port_dict[x]
            if debug:
                print("\n----------- "+x+" -----------")
                pprint.pprint(m)
            
            ## Check if the interface mode is configured as Access
            if interface_settings['mode'] == "access":
                try:
                    Voice_vlan = 0
                    if not interface_settings['voice_Vlan'] == "":
                        Voice_vlan = int(interface_settings['voice_Vlan'])
                except:
                    pass
                try:
                    if not interface_settings['desc'] == "":
                        description = interface_settings["desc"]
                except:
                    interface_settings["desc"] = ""
                try:
                    if not interface_settings['mac'] == []:
                        pass
                except:
                    pass
                try:
                    if not interface_settings['data_Vlan'] == "":
                        data_vlan = int(interface_settings['data_Vlan'])
                except:
                    data_vlan = 1
                try:
                    if not interface_settings['Port_Sec'] == "":
                        mac_limit = interface_settings['Port_Sec']
                except:
                    interface_settings['Port_Sec'] = ""
            
            ## Check the switch that mapped to those catalyst ports
                sw = int(interface_settings['sw_module'])
                if not sw == 0:
                    sw -=1
                if debug:
                    print("Switch Serial Number "+sw_list[sw])
                nm_model = nm_list[sw]
                if debug:
                    print("Switch NM module model is "+nm_model)
                nm_port = "1_" + nm_model + "_" + interface_settings['port']
                ## Find the list of portIds for the NM module
                #
                #
                #
                #
                nm_ports = [d['portId'] for i,d in enumerate(plist) if d['portId'].startswith("1_C3850-NM-4-10G")]
                if debug:
                    print(f"nm_ports for {}")
                
            ## Test if the interface has Port security configured or not then apply the right Meraki configuration
                if debug:
                    print(f"Port_Sec = {interface_settings['Port_Sec']}")
                if interface_settings['Port_Sec'] == "":
                    if debug:
                        print(f"sw = {sw}")
                        print(f"sw_list[sw] = {sw_list[sw]}")
                        print(f"port = {nm_port}")
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
                            nm_port,
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
                        configured_ports[sw].append(nm_port)
                        if debug:
                            print(f"Dashboard response was: {response}")
                        if not Voice_vlan == 0:
                            if debug:
                                print(f"Setting voice vlan to {Voice_vlan}")
                            try:
                                response = dashboard.switch.updateDeviceSwitchPort(
                                    sw_list[sw],
                                    nm_port,
                                    voiceVlan=Voice_vlan
                                )
                                if debug:
                                    print(f"Dashboard response was: {response}")
                            except:
                                pass
                    except:
                        unconfigured_ports[sw].append(nm_port)
                else:
                    if debug:
                        print(f"sw = {sw}")
                        print(f"sw_list[sw] = {sw_list[sw]}")
                        print(f"port = {nm_port}")
                        print(f"name = {description}")
                        print(f"type = access")
                        print(f"vlan = {data_vlan}")
                        print(f"stickyMacAllowList = {json.dumps(interface_settings['mac'])}"),
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
                            nm_port,
                            name=description,
                            enabled=True,
                            type='access',
                            vlan=data_vlan,
                            stickyMacAllowList=json.dumps(interface_settings['mac']),
                            stickyMacAllowListLimit=mac_limit,
                            tags=[],
                            poeEnabled=True,
                            isolationEnabled=False,
                            rstpEnabled=True,
                            stpGuard='disabled',
                            linkNegotiation='Auto negotiate',
                            accessPolicyType='Open'
                        )
                        configured_ports[sw].append(nm_port)
                        if debug:
                            print(f"Dashboard response was: {response}")
                        if not Voice_vlan == 0:
                            if debug:
                                print(f"Setting voice vlan to {Voice_vlan}")
                            try:
                                response = dashboard.switch.updateDeviceSwitchPort(
                                    sw_list[sw],
                                    nm_port,
                                    voiceVlan=Voice_vlan
                                )
                                if debug:
                                    print(f"Dashboard response was: {response}")
                            except:
                                pass
                    except:
                        unconfigured_ports[sw].append(nm_port)
            ## Check if the interface mode is configured as Trunk
            else:
                description = ""
                try:
                    if not interface_settings['desc'] == "":
                        description = interface_settings["desc"]
                except:
                    interface_settings["desc"] = ""
                    description = interface_settings["desc"]
                try:
                    if not interface_settings['native'] == "":
                        native_vlan = int(interface_settings['native'])
                    else:
                        native_vlan = 1
                except:
                    native_vlan = 1
                    interface_settings['native'] = "1"
                try:
                    if not interface_settings['trunk_allowed'] == "":
                        trunk_allow = interface_settings['trunk_allowed']
                    else:
                        trunk_allow = "1-1000"
                except:
                    interface_settings['trunk_allowed'] = "1-1000"
                    trunk_allow = "1-1000"
            
            ## Check the switch that mapped to those catalyst ports
                sw = int(interface_settings['sw_module'])
                if not sw == 0:
                    sw -=1
                if debug:
                    print("Switch Serial Number "+sw_list[sw])
                    print(f"sw = {sw}")
                    print(f"sw_list[{sw}] = {sw_list[sw]}")
                    print(f"port = {nm_port}")
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
                        nm_port,
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
                    configured_ports[sw].append(nm_port)
                    if debug:
                        print(f"Dashboard response was: {response}")
                except:
                    unconfigured_ports[sw].append(nm_port)
                    print("Error in configuring Trunk port "+nm_port)
            if interface_settings["active"] == "false":
                try:
                    response = dashboard.switch.updateDeviceSwitchPort(
                        sw_list[sw],
                        nm_port,
                        enabled=False
                    )
                    configured_ports[sw].append(nm_port)
                    if debug:
                        print(f"Dashboard response was: {response}")
                except:
                    unconfigured_ports[sw].append(nm_port)
                    print("Error in configuring disabled port "+nm_port)
            else:
                pass
            y +=1
    
    loop_configure_meraki_up(port_dict,Uplink_list)
    return configured_ports,unconfigured_ports
'''