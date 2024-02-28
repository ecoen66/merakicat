from netmiko import ConnectHandler
from mc_user_info import *
import re

def Register(host,username,password,port,secret):
    
    debug = DEBUG or DEBUG_REGISTER
    
    issues = list()
    registered_switches = list()
    registered_serials = list()
    
    # We were passed a hostname or IP address...
    host_id = host
    
    # SSH to the switch with netmiko, read the config, grab the hostname,
    # write the config out to a file using the hostname as part of the filespec
    session_info = {
        'device_type': 'cisco_xe',
        'host': host_id,
        'username': username,
        'password': password,
        'port' : port,          # optional, defaults to 22
        'secret': secret,     # optional, defaults to ''
    }
    net_connect = ConnectHandler(**session_info)
    net_connect.enable()
    switch_name = net_connect.find_prompt()
    switch_name = switch_name[:len(switch_name) - 1]
    
    r = net_connect.send_command('show version').split("\n")
    version = r[0].split("Version")[1].strip()
    if debug:
        print(f"In Register, version = {version}")
    v = list(map(int,version.split('.')))
    if debug:
        print(f"In Register, v = {v}")
    if v[0] < 17:
        if v[1] < 10:
            if v[2] < 1:
                issues.append("IOSXE version {version} is less than 17.10.1")
        elif v[1] == 13 and v[2] == 1:
                issues.append("There is a known issue registering to Dashboard from IOSXE 17.13.1")
    
    
    ## If the version was okay...
    ## Check to see if the switch(es) are ALREADY REGISTERED to the Meraki Dashboard
    if len(issues) == 0:
        r = net_connect.send_command('show meraki')
        x=-1
        y=-1
        r_more = r.split("\n")
        ## Find the table in the output
        regex = re.compile("^1  C9")
        x = int([i for i, item in enumerate(r_more) if re.search(regex, item)][0])
        if x == -1:
            return "unsuccessfully", ["No registration status returned."], registered_switches
        y = len(r_more)-x
        z = 0
        while z <= y-1:
            switch_result = r_more[x+z].split()    
            registered_serials.append(switch_result[3])    
            registered_switches.append({
                'Switch': switch_result[0],
                'PID': switch_result[1],
                'Cat Serial': switch_result[2],
                'Meraki Serial': switch_result[3],
                'MAC Address': switch_result[4],
                'Migration Status': switch_result[5],
                'Mode': switch_result[6]
            })
            z += 1
        return "successfully", issues, registered_switches, registered_serials
   
   
   
    ## Check that the "Before you Begin" features are configured
    
    ####  ip name-server
    r = net_connect.send_command('show ip name-servers')
    if len(r)==16 and r[0:15]=='255.255.255.255':
        issues.append("No ip name-server found.")

    ####  interface vlan {vlan-id}
    ####   ip address
    ####   <no shutdown>
    r = net_connect.send_command('show ip int brief | include Vlan')
    r_more = r.split("\n")
    x = 0
    good_vlans = 0
    while x <= len(r_more)-1:
        vlan,ip,ok,method,status,protocol = r_more[x].split()
        if not ip=="unassigned" and status=="up" and protocol=="up":
            good_vlans += 1
        x += 1
    if good_vlans == 0:
        issues.append("No L3 interface found.")

    ####  ip default-gateway  == OR == ip route 0.0.0.0 0.0.0.0
    r = net_connect.send_command('show ip route 0.0.0.0')
    if r == "% Network not in table":
        issues.append("No default route found.")

    ## If we had issues with the "Before you Begin" features, return with issues
    if not len(issues) == 0:
        return "unsuccessfully", issues, registered_switches
    
    
    ## With that out of the way, we can check meraki compatibility
    r = net_connect.send_command('show meraki compatibility')
    #### Add logic to parse for compatibility issues



    ## Register all switches in the stack to the Meraki Dashboard
    r = net_connect.send_command('service meraki register switch all')
    #### Add logic to parse for issues in Conversion Status column
    x=-1
    y=-1
    r_more = r.split("\n")
    if r_more[len(r_more)-1] == "% Are you sure you want to continue? [no]: ":
        r = net_connect.send_command('yes')
        r_more = r.split("\n")
    ## Find the first line of the final results table in the output
    regex = re.compile("^1   C9")
    x = [i for i, item in enumerate(r_more) if re.search(regex, item)]
    ## Find the "Please note..."" line below the table in the output
    regex = re.compile("^Please note")
    y = [i for i, item in enumerate(r_more) if re.search(regex, item)]
    ## Adjust to the last line of the final results table in the output
    y -= 2
    # If there were no lines in the results, then we've got a problem...
    if x == -1:
        return "unsuccessfully", ["No registration status returned."], registered_switches
    # Otherwise, translate the results table into a list of dictionaries - 
    # (one dict per switch) and return that with a success flag
    z = x
    while z <= y:
        switch_result = r_more[z].split()
        registered_serials.append(switch_result[3])    
        registered_switches.append({
            'switch_num': switch_result[0],
            'PID': switch_result[1],
            'cat_serial': switch_result[2],
            'meraki_serial': switch_result[3],
            'mac_address': switch_result[4],
            'migration_status': switch_result[5],
            'mode': switch_result[6]
        })
        z += 1
    return "successfully", issues, registered_switches, registered_serials
