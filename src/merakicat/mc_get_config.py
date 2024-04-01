from netmiko import ConnectHandler
from mc_user_info import DEBUG
import os


def GetConfig(host_id, ios_username, ios_password, ios_port, ios_secret):
    """
    This function will write a Catalyst switch config to a file.
    :param host: The hostname, fqdn or IP address of a switch/stack.
    :return: The hostname, the filespec for the saved config file.
    """

    debug = DEBUG

    Features_configured = list()
    aux_features_config = list()
    host_name = ""

    # SSH to the switch with netmiko, read the config, grab the
    # hostname, write the config out to a file using the hostname
    # as part of the filespec
    session_info = {
        'device_type': 'cisco_xe',
        'host': host_id,
        'username': ios_username,
        'password': ios_password,
        'port': ios_port,          # optional, defaults to 22
        'secret': ios_secret,      # optional, defaults to ''
    }
    net_connect = ConnectHandler(**session_info)
    switch_name = net_connect.find_prompt()
    net_connect.enable()
    switch_name = net_connect.find_prompt()
    switch_name = switch_name[:len(switch_name) - 1]
    net_connect.send_command('term len 0')
    config = net_connect.send_command('show running-config')
    net_connect.send_command('term len 24')
    net_connect.disconnect()
    dir = os.path.join(os.getcwd(), "../../files")
    config_file = os.path.join(dir, switch_name + ".cfg")
    file = open(config_file, "w")
    file.writelines(config)
    file.close()
    return(switch_name, config_file)
