import subprocess
import platform


def Ping(host):
    """
    Returns True if host (str) responds to a ping request.
    Remember that a host may not respond to a ping (ICMP)
    request even if the host name is valid.
    :param host: The host name, FQDN or IP address to ping
    :return: True if reachable, False if not
    """

    # Option for the number of packets as a function of
    param = '-n' if platform.system().lower() == 'windows' else '-c'

    # Building the command. Ex: "ping -c 1 google.com"
    command = ['ping', param, '1', '-q', host]

    return subprocess.call(command, stdout=subprocess.DEVNULL) == 0
