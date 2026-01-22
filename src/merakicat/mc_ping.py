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
    if platform.system().lower() == 'windows':
        result = subprocess.run(f'ping -n 1 {host}', capture_output=True, text=True)
        reachable = result.returncode == 0
    else:
        reachable = subprocess.call(f'ping -c 1 {host} -q', stdout=subprocess.DEVNULL) == 0

    print(f"reachable:  {reachable}")
    
    return reachable
