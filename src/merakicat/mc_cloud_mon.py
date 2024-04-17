from netmiko import ConnectHandler
import meraki
import re
import os
try:
    from mc_user_info import DEBUG
except ImportError:
    DEBUG = False


def CloudSwitch(dashboard, meraki_org, host_id, ios_username, ios_password,
                ios_port, ios_secret):
    """
    This function is under construction....
    It will enroll a Catalyst switch into Dashboard for Cloud Monitoring.
    :param dashboard: Dashboard API session instance
    :param meraki_org: Meraki Organization ID
    :param host_id: The switch or stack to SSH into
    :param ios_username: Username for SSH
    :param ios_password: Password for SSH
    :param ios_port: Port number for SSH
    :param ios_secret: IOSXE secret password for CLI escalation
    :return: (I'm not sure yet what I will return other than success/failure')
    """

    debug = DEBUG

    devices = list()
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
    sudi_chain = net_connect.send_command(
      'show cry pki certificates pem CISCO_IDEVID_SUDI')
    regex = re.compile(r"%\sGeneral Purpose Certificate:\s *", flags=re.I)
    if len(regex.split(sudi_chain)) > 1:
        if not regex.split(sudi_chain)[1] == "":
            maybe_sudi = regex.split(sudi_chain)[1]
            print(f"maybe_sudi = \n{maybe_sudi}")
            sudi = maybe_sudi.replace('\n','\n        ')
            print(f"sudi = \n{sudi}")

    net_connect.send_command('term len 24')
    net_connect.disconnect()

    dir = os.path.join(os.getcwd(), "../../files")
    config_file = os.path.join(dir, switch_name + ".cfg")
    file = open(config_file, "w")
    file.writelines(config)
    file.close()

    dev_info = {
        "sudi": sudi,
        "tunnel": {
            "certificateName": "CISCO_IDEVID_SUDI",
            "name": "MERAKI-PRIMARY",
            "loopbackNumber": 1000,
            "localInterface": 1
        },
        "user": { "username": "meraki-user" },
        "vty": {
            "startLineNumber": 16,
            "endLineNumber": 19,
            "authentication": {
                "group": {
                    "name": "MERAKI"
                }
            },
            "authorization": {
                "group": {
                    "name": "MERAKI"
                }
            },
            "accessList": {
                "vtyIn": {
                    "name": "MERAKI_IN"
                },
                "vtyOut": {
                    "name": "MERAKI_OUT"
                }
            },
            "rotaryNumber": 50
        }
    }

    dev_info2 = {
        "sudi": sudi
    }

    devices.append(dev_info2)
    # devices = []
    # devices = [{'sudi': '-----BEGIN CERTIFICATE-----\n        MIIDyTCCArGgAwIBAgIKBBNXOVCGU1YztjANBgkqhkiG9w0BAQsFADAnMQ4wDAYD\n        VQQKEwVDaXNjbzEVMBMGA1UEAxMMQUNUMiBTVURJIENBMB4XDTIxMDUzMTEzNTUx\n        NVoXDTI5MDUxNDIwMjU0MVowbTEpMCcGA1UEBRMgUElEOkM5MjAwTC0yNFAtNEcg\n        U046SkFFMjUyMjBSMksxDjAMBgNVBAoTBUNpc2NvMRgwFgYDVQQLEw9BQ1QtMiBM\n        aXRlIFNVREkxFjAUBgNVBAMTDUM5MjAwTC0yNFAtNEcwggEiMA0GCSqGSIb3DQEB\n        AQUAA4IBDwAwggEKAoIBAQDaUPxW76gT5MdoEAt+UrDFiYA9RYh2iHicDViBEyow\n        TR1TuP36bHh13X3vtGiDsCD88Ci2TZIqd/EDkkc7v9ipUUYVVH+YDrPt2Aukb1PH\n        D6K0R+KhgEzRo5x54TlU6oWvjUpwNZUwwdhMWIQaUVkMyZBYNy0jGPLO8jwZhyBg\n        1Fneybr9pwedGbLrAaz+gdEikB8B4a/fvPjVfL5Ngb4QRjFqWuE+X3nLc0kHedep\n        6nfgpUNXMlStVm5nIXKP6OjmzfCHPYh9L2Ehs1TrSk1ser9Ofx0ZMVL/jBZR2EIj\n        OZ8tH6KlX2/B2pbSPIO6kD5c4UA8Cf1SbDJCwJ/kI9ihAgMBAAGjgbAwga0wDgYD\n        VR0PAQH/BAQDAgXgMAwGA1UdEwEB/wQCMAAwHwYDVR0jBBgwFoAUSNjx8cJw1Vu7\n        fHMJk6+4uDAD+H8wTQYDVR0RBEYwRKBCBgkrBgEEAQkVAgOgNRMzQ2hpcElEPVVV\n        VUNNaElGcUVFMklFUUVBQWNBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE9MB0GA1Ud\n        DgQWBBRdhMkFD/z5hokaQeLbaRsp4hkvbzANBgkqhkiG9w0BAQsFAAOCAQEAMtuh\n        YpBz4xEZ7YdJsLpw67Q0TTJGnTBRpzAeY1urYDoDz8TSx556XG7z3IRzuED5KVSp\n        OwmH/iZ+tDfYQ3W3ElWTW93871DkuW4WQIfbnoHg/F7bF0DKYVkD3rpZjyz3NhzH\n        d7cjTdJXQ85bTAOXDuxKH3qewrXxxOGXgh3I6NUq0UwMTWh84lND7Jl+ZAQkYNS2\n        iHanTZFQBk3ML0NUb7fKDYGRTZRqwQ/upIO4S6LV1cxH/6V0qbMy3sCSHZoMLrW3\n        0m3M6yKpe5+VZzHZwmWdUf3Ot+zKjhveK5/YNsMIASdvtvymxUizq2Hr1hvR/kPc\n        p1vuyWxipU8JfzOh/A==\n        -----END CERTIFICATE-----\n        ', 'tunnel': {'certificateName': 'DeviceSUDI', 'name': 'MERAKI', 'loopbackNumber': 1000, 'localInterface': 1}, 'user': {'username': 'Meraki'}, 'vty': {'startLineNumber': 16, 'endLineNumber': 17, 'authentication': {'group': {'name': ''}}, 'authorization': {'group': {'name': 'MERAKI'}}, 'accessList': {'vtyIn': {'name': 'MERAKI_IN'}, 'vtyOut': {'name': 'MERAKI_OUT'}}, 'rotaryNumber': 50}}]

    print(f"devices = {devices}")
    print(f"meraki_org = {meraki_org}")
    response = dashboard.organizations.getOrganizationInventoryOnboardingCloudMonitoringNetworks(meraki_org, 'switch', total_pages='all')
    print(f"Response = {response}")
    response = dashboard.organizations.createOrganizationInventoryOnboardingCloudMonitoringPrepare(meraki_org, devices)
    print(f"Response = {response}")
    return(switch_name, config_file)
