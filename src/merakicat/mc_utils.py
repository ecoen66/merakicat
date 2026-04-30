# Common utility funcitons / classes

def normalize_mac(mac_address: str) -> str:
    """Convert dotted Cisco MAC format into colon-separated octets."""
    compact_mac = mac_address.strip().lower().replace(".", "")
    return ":".join(
        compact_mac[index : index + 2] for index in range(0, len(compact_mac), 2)
    )
