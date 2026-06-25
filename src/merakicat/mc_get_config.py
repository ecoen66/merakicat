import os

from netmiko import ConnectHandler

from mc_constants import DEFAULT_FILES_FOLDER
from mc_prechecks import prechecks

try:
    from mc_user_info import DEBUG
except ImportError:
    DEBUG = False


def GetConfig(
    host_id,
    ios_username,
    ios_password,
    ios_port,
    ios_secret,
    *,
    run_prechecks: bool = False,
):
    """
    Write a Catalyst switch config to a file.

    Parameters:
        host_id: The hostname, fqdn or IP address of a switch/stack.
        ios_username: Username for SSH.
        ios_password: Password for SSH.
        ios_port: Port number for SSH.
        ios_secret: IOSXE secret password for CLI escalation.
        run_prechecks: When True, run registration readiness checks in the
            same SSH session and return a third value (PrecheckResult).

    Returns:
        When run_prechecks is False: (switch_name, config_file).
        When run_prechecks is True: (switch_name, config_file, PrecheckResult).
    """

    debug = DEBUG

    Features_configured = list()
    aux_features_config = list()
    host_name = ""

    session_info = {
        "device_type": "cisco_xe",
        "host": host_id,
        "username": ios_username,
        "password": ios_password,
        "port": ios_port,
        "secret": ios_secret,
    }
    net_connect = ConnectHandler(**session_info)
    switch_name = net_connect.find_prompt()
    net_connect.enable()
    switch_name = net_connect.find_prompt()
    switch_name = switch_name[: len(switch_name) - 1]
    net_connect.send_command("term len 0")
    precheck_result = prechecks(net_connect) if run_prechecks else None
    config = net_connect.send_command("show running-config")
    net_connect.disconnect()
    dir = os.path.join(os.getcwd(), DEFAULT_FILES_FOLDER)
    config_file = os.path.join(dir, switch_name + ".cfg")
    file = open(config_file, "w")
    file.writelines(config)
    file.close()
    if run_prechecks:
        return switch_name, config_file, precheck_result
    return switch_name, config_file
