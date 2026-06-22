import meraki


def get_networks(dashboard_api: meraki.DashboardAPI, organization_id: str) -> str:
    """
    Return a formatted list of Meraki networks for an organization.

    Parameters:
    dashboard_api (meraki.DashboardAPI): Active dashboard API client.
    organization_id (str): Dashboard organization ID.

    Returns:
    str: Markdown-friendly list of network names and IDs, or a message.
    """
    if organization_id.strip() == "":
        return (
            "I'm sorry, but I don't have a valid Meraki organization ID. "
            "Check your configured organization name."
        )

    try:
        networks = dashboard_api.organizations.getOrganizationNetworks(
            organizationId=organization_id
        )
    except meraki.exceptions.APIError:  # type: ignore
        return (
            "I'm sorry, but I was unable to get the list of networks for "
            "the configured organization."
        )

    if len(networks) == 0:
        return "No Meraki networks were found for the configured organization."

    lines = [f"Found {len(networks)} network(s):"]
    for network in sorted(networks, key=lambda item: item.get("name", "").lower()):
        net_name = network.get("name", "(unnamed network)")
        lines.append(f"- {net_name}")
    return "\n".join(lines)
