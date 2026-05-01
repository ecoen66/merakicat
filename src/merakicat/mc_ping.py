import subprocess
import platform


def Ping(host, quiet=False):
    """
    Returns True if host (str) responds to a ping request.
    Remember that a host may not respond to a ping (ICMP)
    request even if the host name is valid.
    :param host: The host name, FQDN or IP address to ping
    :param quiet: If True, do not print reachability to stdout
    :return: True if reachable, False if not
    """

    # Option for the number of packets as a function of
    if platform.system().lower() == "windows":
        result = subprocess.run(f"ping -n 1 {host}", capture_output=True, text=True)
        reachable = result.returncode == 0
    else:
        reachable = (
            subprocess.call(
                f"ping -c 1 {host} -q", shell=True, stdout=subprocess.DEVNULL
            )
            == 0
        )

    if not quiet:
        print(f"reachable:  {reachable}")

    return reachable
