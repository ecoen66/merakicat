# -*- coding: utf-8 -*-
"""IOS software upgrade helpers for Catalyst switches."""

from __future__ import annotations

import logging
import os
import re
import time
import urllib.parse
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from mc_constants import DEFAULT_PARALLEL_MAX_WORKERS
from mc_min_ios_version import mc_min_ios_version
from mc_parallel import run_parallel_indexed
from mc_ping import Ping
from mc_utils import (
    check_minimum_ios_version,
    get_switch_model,
    parse_ios_version,
    version_tuple,
)

import requests
from netmiko import ConnectHandler
from netmiko.exceptions import ConnectionException, NetmikoTimeoutException
from paramiko.ssh_exception import AuthenticationException, SSHException

logger = logging.getLogger(__name__)

REQUESTS_TIMEOUT = 30
UPGRADE_COMMAND_TIMEOUT_SECONDS = 3600
UPGRADE_REBOOT_DOWN_TIMEOUT_SECONDS = 1200
UPGRADE_REBOOT_UP_TIMEOUT_SECONDS = 1800
UPGRADE_REBOOT_POLL_SECONDS = 10
UPGRADE_SSH_READY_TIMEOUT_SECONDS = 300
# Seconds of channel silence that ends one read pass. Kept short so prompts
# are answered promptly; the operation loop keeps waiting until the switch
# returns its CLI prompt.
UPGRADE_READ_QUIET_SECONDS = 2
# Give up on a command after this much complete silence with no CLI prompt.
UPGRADE_MAX_IDLE_SECONDS = 900
UPGRADE_CONFIG_COMMAND_TIMEOUT_SECONDS = 120
COMMAND_LOG_STATUS_PREFIX = "status:"
UPGRADE_SUMMARY_TITLE = "Upgrade summary by switch:"
# Prompt replies and routine config-mode noise omitted from console Issuing lines.
QUIET_ISSUED_COMMANDS = frozenset({"<enter>", "end", "conf t", "y"})
LISTING_HREF_PATTERN = re.compile(
    r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE
)

IOS_SOFTWARE_DIR_NAME = "ios-software"
IOS_SOFTWARE_DIR_OPTIONS = ("--ios-software", "--ios_software")


class UpgradeStatus(str, Enum):
    """Outcome status for a single-host upgrade attempt."""

    SUCCESS = "success"
    FAILURE = "failure"
    NOT_SUPPORTED = "not_supported"
    WOULD_UPGRADE = "would_upgrade"
    WOULD_DOWNGRADE = "would_downgrade"
    ALREADY_CURRENT = "already_current"
    DOWNGRADE_BLOCKED = "downgrade_blocked"


@dataclass(frozen=True)
class UpgradeResult:
    """Result of upgrading (or probing) a single host."""

    host: str
    status: UpgradeStatus
    message: str
    model: str = ""
    image: str = ""
    current_version: str = ""
    command_log: tuple[str, ...] = ()


def normalize_software_url(url: str) -> str:
    """Ensure the software base URL ends with a single trailing slash.

    Parameters:
        url (str): Base URL that serves the ios-software directory.

    Returns:
        str: Normalized URL ending with '/'.
    """
    stripped = url.strip()
    if not stripped:
        return stripped
    return stripped.rstrip("/") + "/"


def resolve_ios_software_dir(ios_software_dir: str | None = None) -> str:
    """Locate the local ios-software directory.

    Parameters:
        ios_software_dir (str | None): Optional path that replaces the default
            search. Relative paths are resolved from the current directory.
            When that location is not a directory, the same path is also
            tried from ../.. .

    Returns:
        str: Absolute path to the ios-software directory.

    Raises:
        FileNotFoundError: If no ios-software directory can be found.
    """
    if ios_software_dir is not None and ios_software_dir.strip():
        specified = os.path.expanduser(ios_software_dir.strip())
        candidates = [
            specified,
            os.path.join("..", "..", specified),
        ]
        tried: list[str] = []
        for path in candidates:
            normalized = os.path.abspath(path)
            if normalized in tried:
                continue
            tried.append(normalized)
            if os.path.isdir(normalized):
                return normalized
        raise FileNotFoundError(
            "ios-software directory not found: " + ", ".join(tried)
        )
    package_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.getcwd(), IOS_SOFTWARE_DIR_NAME),
        os.path.join(os.getcwd(), "..", "..", IOS_SOFTWARE_DIR_NAME),
        os.path.join(package_dir, "..", "..", IOS_SOFTWARE_DIR_NAME),
    ]
    for path in candidates:
        normalized = os.path.normpath(path)
        if os.path.isdir(normalized):
            return normalized
    raise FileNotFoundError(
        f"Unable to find the '{IOS_SOFTWARE_DIR_NAME}' directory."
    )


def get_sw_name_prefix(model: str) -> str:
    """Return the software directory prefix for a switch model.

    Parameters:
        model (str): Switch model identifier from show inventory.

    Returns:
        str: sw_name_prefix value, or empty string when unavailable.
    """
    entry = mc_min_ios_version.get(model)
    if isinstance(entry, dict):
        return str(entry.get("sw_name_prefix", ""))
    return ""


class SoftwareServerUnavailable(Exception):
    """The software HTTP server could not be contacted."""


class SoftwareServerLayoutError(Exception):
    """The software HTTP server directory layout is not valid for upgrade."""


@dataclass(frozen=True)
class ServedBin:
    """One image file served from a platform directory."""

    filename: str
    content_length: int | None


def known_sw_name_prefixes() -> list[str]:
    """Return sorted platform directory names used by supported switch models.

    Returns:
        list[str]: Unique sw_name_prefix values, such as cat9k and ie35xx.
    """
    prefixes: set[str] = set()
    for entry in mc_min_ios_version.values():
        if not isinstance(entry, dict):
            continue
        prefix = str(entry.get("sw_name_prefix", "")).strip()
        if prefix:
            prefixes.add(prefix)
    return sorted(prefixes)


def expected_software_layout_hint() -> str:
    """Describe the ios-software directories an upgrade requires.

    Returns:
        str: Operator-facing layout hint.
    """
    rendered = ", ".join(f"{prefix}/" for prefix in known_sw_name_prefixes())
    return (
        "Each of these directories must exist and contain at most one .bin file: "
        f"{rendered}."
    )


def bin_files_in_directory(prefix_dir: str) -> list[str]:
    """Return sorted .bin filenames directly inside a platform directory.

    Parameters:
        prefix_dir (str): Absolute or relative platform directory.

    Returns:
        list[str]: Basenames ending in .bin, case-insensitive.
    """
    names: list[str] = []
    for name in os.listdir(prefix_dir):
        if not name.lower().endswith(".bin"):
            continue
        if os.path.isfile(os.path.join(prefix_dir, name)):
            names.append(name)
    return sorted(names)


def single_bin_filename_error(prefix_dir: str, bin_filenames: list[str]) -> str:
    """Return an error when a directory does not contain exactly one .bin file.

    Parameters:
        prefix_dir (str): Directory that was inspected.
        bin_filenames (list[str]): .bin basenames found in that directory.

    Returns:
        str: Error text, or empty string when the directory has one .bin file.
    """
    if len(bin_filenames) == 0:
        return f"No .bin file found in '{prefix_dir}'."
    if len(bin_filenames) > 1:
        names = ", ".join(bin_filenames)
        return (
            f"Multiple .bin files found in '{prefix_dir}': {names}. "
            "Keep at most one .bin file per directory."
        )
    return ""


def resolve_bin_filename(sw_name_prefix: str, ios_software_dir: str | None = None) -> str:
    """Resolve the single .bin filename for a software prefix directory.

    Parameters:
        sw_name_prefix (str): Directory name under ios-software.
        ios_software_dir (str | None): Optional override for ios-software root.

    Returns:
        str: Basename of the single .bin file.

    Raises:
        ValueError: If zero or more than one .bin file is present.
        FileNotFoundError: If the prefix directory does not exist.
    """
    root = ios_software_dir if ios_software_dir is not None else resolve_ios_software_dir()
    prefix_dir = os.path.join(root, sw_name_prefix)
    if not os.path.isdir(prefix_dir):
        raise FileNotFoundError(
            f"Software directory not found for prefix '{sw_name_prefix}': {prefix_dir}"
        )
    bin_filenames = bin_files_in_directory(prefix_dir)
    error = single_bin_filename_error(prefix_dir, bin_filenames)
    if error:
        raise ValueError(error)
    return bin_filenames[0]


def validate_local_software_layout(ios_software_root: str) -> dict[str, str]:
    """Require every platform directory, each with at most one .bin file.

    An empty platform directory is valid. More than one .bin file is not.

    Parameters:
        ios_software_root (str): Local ios-software directory.

    Returns:
        dict[str, str]: Platform directories that contain one .bin file.

    Raises:
        ValueError: If any platform directory is missing or contains more
            than one .bin file.
    """
    errors: list[str] = []
    found: dict[str, str] = {}
    for prefix in known_sw_name_prefixes():
        prefix_dir = os.path.join(ios_software_root, prefix)
        if not os.path.isdir(prefix_dir):
            errors.append(f"Missing directory '{prefix}' in '{ios_software_root}'.")
            continue
        bin_filenames = bin_files_in_directory(prefix_dir)
        if len(bin_filenames) == 0:
            continue
        if len(bin_filenames) > 1:
            names = ", ".join(bin_filenames)
            errors.append(
                f"Multiple .bin files found in '{prefix_dir}': {names}. "
                "Keep at most one .bin file per directory."
            )
            continue
        found[prefix] = bin_filenames[0]
    if errors:
        detail = "\n".join(f"- {error}" for error in errors)
        raise ValueError(
            "Local ios-software directory layout is invalid:\n"
            f"{detail}\n{expected_software_layout_hint()}"
        )
    return found


def directory_listing_body(body: str) -> bool:
    """Return True when HTML looks like an HTTP directory listing.

    Parameters:
        body (str): Response body.

    Returns:
        bool: True for Python http.server and typical autoindex pages.
    """
    lowered = body.lower()
    if "directory listing for" in lowered:
        return True
    return "index of " in lowered


def http_listing_entries(body: str) -> list[str]:
    """Return file and directory names linked from a directory listing.

    Directory names keep a trailing slash. Parent-directory and sort links
    are omitted.

    Parameters:
        body (str): HTML directory listing.

    Returns:
        list[str]: Unique entry names in listing order.
    """
    entries: list[str] = []
    seen: set[str] = set()
    for raw_href in LISTING_HREF_PATTERN.findall(body):
        href = urllib.parse.unquote(raw_href.split("#", 1)[0])
        parsed = urllib.parse.urlparse(href)
        path = parsed.path if parsed.scheme or parsed.netloc else href
        path = path.split("?", 1)[0]
        if path in {"", "/", ".", "./", "..", "../"}:
            continue
        is_directory = path.endswith("/")
        segment = path.rstrip("/").split("/")[-1]
        if segment in {"", ".", ".."}:
            continue
        name = f"{segment}/" if is_directory else segment
        if name in seen:
            continue
        seen.add(name)
        entries.append(name)
    return entries


def perform_http_request(
    session: requests.Session,
    url: str,
    *,
    method: str,
    stream: bool = False,
) -> requests.Response:
    """Send GET or HEAD and map transport failures to SoftwareServerUnavailable.

    Parameters:
        session (requests.Session): Session used for the request.
        url (str): Absolute URL.
        method (str): Either 'GET' or 'HEAD'.
        stream (bool): When True, leave the response body unread.

    Returns:
        requests.Response: Completed response, including non-200 statuses.

    Raises:
        SoftwareServerUnavailable: When the server cannot be contacted.
    """
    request_method = session.get if method == "GET" else session.head
    try:
        return request_method(
            url,
            timeout=REQUESTS_TIMEOUT,
            allow_redirects=True,
            stream=stream,
        )
    except requests.Timeout as exc:
        logger.error("perform_http_request: Request timed out: %s", exc)
        raise SoftwareServerUnavailable(f"HTTP server timed out at {url}.") from exc
    except requests.ConnectionError as exc:
        logger.error("perform_http_request: Connection failed: %s", exc)
        raise SoftwareServerUnavailable(
            http_server_unavailable_message(url)
        ) from exc
    except requests.HTTPError as exc:
        logger.error("perform_http_request: HTTP error occurred: %s", exc)
        raise SoftwareServerUnavailable(
            f"HTTP server request failed for {url}: {exc}"
        ) from exc
    except requests.RequestException as exc:
        logger.error("perform_http_request: Request failed: %s", exc)
        raise SoftwareServerUnavailable(
            f"HTTP server request failed for {url}: {exc}"
        ) from exc


def http_server_unavailable_message(url: str) -> str:
    """Return operator guidance when the software HTTP server is down.

    Parameters:
        url (str): URL that could not be contacted.

    Returns:
        str: Error text including how to start the included server.
    """
    return (
        f"HTTP server is not available at {url}. "
        "Start it with 'python3 http-server.py' from the ios-software directory, "
        "then re-run the upgrade."
    )


def fetch_directory_listing(session: requests.Session, url: str) -> str:
    """GET a URL and require an HTTP directory listing.

    Parameters:
        session (requests.Session): Session used for the request.
        url (str): Absolute URL of a directory, with a trailing slash.

    Returns:
        str: Listing HTML.

    Raises:
        SoftwareServerUnavailable: When the server cannot be contacted or the
            root URL is not found.
        SoftwareServerLayoutError: When the body is not a directory listing.
    """
    response = perform_http_request(session, url, method="GET")
    try:
        if response.status_code == 404:
            raise SoftwareServerUnavailable(
                f"HTTP server returned HTTP 404 for {url}. "
                f"{expected_software_layout_hint()}"
            )
        if response.status_code != 200:
            logger.error(
                "fetch_directory_listing: HTTP error occurred: HTTP %s for %s",
                response.status_code,
                url,
            )
            raise SoftwareServerUnavailable(
                f"HTTP server returned HTTP {response.status_code} for {url}."
            )
        body = response.text
    finally:
        response.close()
    if not directory_listing_body(body):
        raise SoftwareServerLayoutError(
            f"HTTP server at {url} did not return a directory listing. "
            f"{expected_software_layout_hint()}"
        )
    return body


def listing_bin_names(entries: list[str]) -> list[str]:
    """Return .bin filenames from directory-listing entries.

    Parameters:
        entries (list[str]): Names from http_listing_entries.

    Returns:
        list[str]: Entries that are files ending in .bin.
    """
    return [
        entry
        for entry in entries
        if not entry.endswith("/") and entry.lower().endswith(".bin")
    ]


def content_length_header(response: requests.Response) -> int | None:
    """Parse a Content-Length header.

    Parameters:
        response (requests.Response): HEAD or GET response.

    Returns:
        int | None: Byte length, or None when the header is absent or invalid.
    """
    raw_length = response.headers.get("Content-Length")
    if raw_length is None:
        return None
    try:
        return int(raw_length)
    except ValueError:
        return None


def served_bin_for_url(session: requests.Session, bin_url: str, filename: str) -> ServedBin:
    """Confirm one image URL is fetchable and capture its size.

    Parameters:
        session (requests.Session): Session used for the request.
        bin_url (str): Absolute URL of the .bin file.
        filename (str): Basename expected in the directory listing.

    Returns:
        ServedBin: Filename and Content-Length when the server provides one.

    Raises:
        SoftwareServerLayoutError: When the image URL is not available.
        SoftwareServerUnavailable: When the server cannot be contacted.
    """
    response = perform_http_request(session, bin_url, method="HEAD")
    if response.status_code == 405:
        response.close()
        response = perform_http_request(session, bin_url, method="GET", stream=True)
    try:
        if response.status_code != 200:
            logger.error(
                "served_bin_for_url: HTTP error occurred: HTTP %s for %s",
                response.status_code,
                bin_url,
            )
            raise SoftwareServerLayoutError(
                f"Image file is not available at {bin_url} "
                f"(HTTP {response.status_code})."
            )
        return ServedBin(
            filename=filename,
            content_length=content_length_header(response),
        )
    finally:
        response.close()


def read_http_software_tree(
    software_url: str,
) -> tuple[dict[str, ServedBin], str]:
    """Read platform directories from the software HTTP server.

    Parameters:
        software_url (str): Base URL serving the ios-software directory.

    Returns:
        tuple[dict[str, ServedBin], str]: Served images keyed by platform
        directory, and an error message when the layout is invalid. The error
        message is empty when every directory exists and has at most one .bin
        file. Directories with no .bin file are omitted from the mapping.

    Raises:
        SoftwareServerUnavailable: When the server cannot be contacted.
        SoftwareServerLayoutError: When the base URL is not a directory listing.
    """
    base = normalize_software_url(software_url)
    if not base:
        raise SoftwareServerLayoutError("No software URL provided.")
    prefixes = known_sw_name_prefixes()
    errors: list[str] = []
    served: dict[str, ServedBin] = {}
    with requests.Session() as session:
        root_body = fetch_directory_listing(session, base)
        root_entries = http_listing_entries(root_body)
        root_bins = listing_bin_names(root_entries)
        if root_bins:
            names = ", ".join(root_bins)
            errors.append(
                f"The server root contains .bin files ({names}). "
                "Point the URL at the ios-software directory, not a platform subdirectory."
            )
        for prefix in prefixes:
            dir_url = urllib.parse.urljoin(base, urllib.parse.quote(prefix) + "/")
            try:
                body = fetch_directory_listing(session, dir_url)
            except SoftwareServerUnavailable as exc:
                message = str(exc)
                if "HTTP 404" in message:
                    errors.append(f"Missing directory '{prefix}/'.")
                    continue
                raise
            except SoftwareServerLayoutError as exc:
                errors.append(str(exc))
                continue
            bin_names = listing_bin_names(http_listing_entries(body))
            if len(bin_names) == 0:
                continue
            if len(bin_names) > 1:
                names = ", ".join(bin_names)
                errors.append(
                    f"Directory '{prefix}/' has multiple .bin files ({names}). "
                    "Keep at most one .bin file per directory."
                )
                continue
            bin_url = urllib.parse.urljoin(
                dir_url, urllib.parse.quote(bin_names[0])
            )
            try:
                served[prefix] = served_bin_for_url(session, bin_url, bin_names[0])
            except SoftwareServerLayoutError as exc:
                errors.append(str(exc))
    if not errors:
        return served, ""
    detail = "\n".join(f"- {error}" for error in errors)
    layout_error = (
        f"HTTP server at {base} does not have the required software layout.\n"
        f"{detail}\n{expected_software_layout_hint()}"
    )
    return served, layout_error


def local_remote_mismatch(
    ios_software_root: str,
    local_bins: dict[str, str],
    remote_bins: dict[str, ServedBin],
) -> str:
    """Return an error when local images differ from the HTTP server.

    Parameters:
        ios_software_root (str): Local ios-software directory.
        local_bins (dict[str, str]): Platform directory to local .bin filename.
        remote_bins (dict[str, ServedBin]): Platform directory to served image.

    Returns:
        str: Error text, or empty string when names and sizes match.
    """
    errors: list[str] = []
    prefixes = sorted(set(local_bins) | set(remote_bins))
    for prefix in prefixes:
        local_name = local_bins.get(prefix, "")
        remote = remote_bins.get(prefix)
        if local_name and remote is None:
            errors.append(
                f"Directory '{prefix}/' has '{local_name}' in '{ios_software_root}' "
                "but the server has no .bin file."
            )
            continue
        if remote is not None and not local_name:
            errors.append(
                f"Directory '{prefix}/' serves '{remote.filename}' "
                f"but '{ios_software_root}' has no .bin file."
            )
            continue
        if remote.filename != local_name:
            errors.append(
                f"Directory '{prefix}/' serves '{remote.filename}' "
                f"but '{ios_software_root}' has '{local_name}'."
            )
            continue
        if remote.content_length is None:
            continue
        local_size = os.path.getsize(
            os.path.join(ios_software_root, prefix, local_name)
        )
        if remote.content_length != local_size:
            errors.append(
                f"Image '{prefix}/{local_name}' is {remote.content_length} bytes "
                f"on the server and {local_size} bytes in '{ios_software_root}'."
            )
    if not errors:
        return ""
    detail = "\n".join(f"- {error}" for error in errors)
    return (
        "HTTP server files do not match the local ios-software directory:\n"
        f"{detail}"
    )


def preflight_software_server(
    software_url: str,
    ios_software_dir: str | None = None,
) -> str:
    """Verify the HTTP server and image layout before contacting switches.

    Confirms the server is reachable, then checks that every platform
    directory exists on that server and locally with at most one .bin file.
    Directories with no image are allowed. Images that are present must match.

    Parameters:
        software_url (str): Base URL serving the ios-software directory.
        ios_software_dir (str | None): Local image directory. When omitted,
            the default ios-software location is used.

    Returns:
        str: Empty string when the server and layout are ready, otherwise
        an operator-facing error message.
    """
    try:
        root = resolve_ios_software_dir(ios_software_dir)
    except FileNotFoundError as exc:
        return str(exc)

    remote_bins: dict[str, ServedBin] = {}
    remote_error = ""
    try:
        remote_bins, remote_error = read_http_software_tree(software_url)
    except SoftwareServerUnavailable as exc:
        return str(exc)
    except SoftwareServerLayoutError as exc:
        remote_error = str(exc)

    local_bins: dict[str, str] = {}
    local_error = ""
    try:
        local_bins = validate_local_software_layout(root)
    except ValueError as exc:
        local_error = str(exc)

    mismatch_error = ""
    if not remote_error and not local_error:
        mismatch_error = local_remote_mismatch(root, local_bins, remote_bins)

    parts = [part for part in (remote_error, local_error, mismatch_error) if part]
    return "\n".join(parts)


def build_copy_source(software_url: str, sw_name_prefix: str, bin_filename: str) -> str:
    """Build the remote source path used by the IOS copy command.

    Parameters:
        software_url (str): Base URL serving ios-software.
        sw_name_prefix (str): Model software prefix directory.
        bin_filename (str): Image filename.

    Returns:
        str: Concatenated URL path for copy.
    """
    base = normalize_software_url(software_url)
    return f"{base}{sw_name_prefix}/{bin_filename}"


def version_from_bin_filename(bin_filename: str) -> str:
    """Extract the dotted IOS version embedded in an image filename.

    Parameters:
        bin_filename (str): Image basename such as cat9k_iosxe.17.18.04.SPA.bin.

    Returns:
        str: Version string, or empty string when none is found.
    """
    match = re.search(r"(\d+(?:\.\d+)+)", bin_filename)
    if not match:
        return ""
    return match.group(1)


def format_current_versions(versions: list[str]) -> str:
    """Format one or more stack member versions for display.

    Parameters:
        versions (list[str]): Parsed SW Version values.

    Returns:
        str: Comma-separated versions, or 'unknown' when empty.
    """
    if not versions:
        return "unknown"
    return ", ".join(versions)


def stack_already_on_target(versions: list[str], target_version: str) -> bool:
    """Return True when every stack member matches the target image version.

    Parameters:
        versions (list[str]): Running SW Version values.
        target_version (str): Version extracted from the .bin filename.

    Returns:
        bool: True when all members equal the target (numeric compare).
    """
    if not versions or not target_version:
        return False
    target = version_tuple(target_version)
    return all(version_tuple(version) == target for version in versions)


def classify_version_change(versions: list[str], target_version: str) -> str:
    """Classify how running versions relate to the served image version.

    Parameters:
        versions (list[str]): Running SW Version values.
        target_version (str): Version extracted from the .bin filename.

    Returns:
        str: One of 'current', 'upgrade', 'downgrade', or 'mixed'.
    """
    if stack_already_on_target(versions, target_version):
        return "current"
    if not versions or not target_version:
        return "upgrade"
    target = version_tuple(target_version)
    has_older = any(version_tuple(version) < target for version in versions)
    has_newer = any(version_tuple(version) > target for version in versions)
    if has_older and has_newer:
        return "mixed"
    if has_newer:
        return "downgrade"
    return "upgrade"


def missing_ios_software_dir_message() -> str:
    """Return the error text used when --ios-software has no directory.

    Returns:
        str: Operator-facing error message.
    """
    return (
        "A directory path is required after --ios-software. "
        "Example: upgrade host 10.0.0.1 --ios-software /path/to/ios-software"
    )


def inline_ios_software_dir(token: str) -> str | None:
    """Return the directory from a --ios-software=path token.

    Parameters:
        token (str): One command token.

    Returns:
        str | None: Directory text after '=', or None when token is not that form.
        An empty string means the option was present without a path.
    """
    for option in IOS_SOFTWARE_DIR_OPTIONS:
        prefix = option + "="
        if token.startswith(prefix):
            return token[len(prefix) :]
    return None


def is_upgrade_option(token: str) -> bool:
    """Return True when token is an upgrade flag rather than a path or target.

    Parameters:
        token (str): One command token.

    Returns:
        bool: True for -y, --allow-downgrade, and --ios-software forms.
    """
    if token in {"-y", "--allow-downgrade", "--allow_downgrade"}:
        return True
    if token in IOS_SOFTWARE_DIR_OPTIONS:
        return True
    return inline_ios_software_dir(token) is not None


def take_ios_software_dir(tokens: list[str]) -> tuple[list[str], str | None]:
    """Remove --ios-software and its path from a token list.

    Parameters:
        tokens (list[str]): Command tokens that may include the option.

    Returns:
        tuple[list[str], str | None]: Remaining tokens, and the directory path
        when one was provided.

    Raises:
        ValueError: If the option is repeated or has no directory path.
    """
    remaining: list[str] = []
    directory: str | None = None
    index = 0
    while index < len(tokens):
        token = tokens[index]
        inline = inline_ios_software_dir(token)
        if inline is not None:
            if directory is not None:
                raise ValueError("Specify --ios-software only once.")
            if not inline:
                raise ValueError(missing_ios_software_dir_message())
            directory = inline
            index += 1
            continue
        if token in IOS_SOFTWARE_DIR_OPTIONS:
            if directory is not None:
                raise ValueError("Specify --ios-software only once.")
            if index + 1 >= len(tokens) or is_upgrade_option(tokens[index + 1]):
                raise ValueError(missing_ios_software_dir_message())
            directory = tokens[index + 1]
            index += 2
            continue
        remaining.append(token)
        index += 1
    return remaining, directory


def parse_upgrade_cli_tokens(rest: str) -> tuple[str, bool, str | None, bool, str | None]:
    """Parse target, flags, optional URL, and ios-software directory from text.

    Parameters:
        rest (str): Remainder of the user command after 'host ' or 'hosts '.

    Returns:
        tuple[str, bool, str | None, bool, str | None]: target, yes_flag,
        software_url, allow_downgrade, ios_software_dir.

    Raises:
        ValueError: If --ios-software is present without a directory path.
    """
    tokens, ios_software_dir = take_ios_software_dir(rest.split())
    yes_flag = False
    allow_downgrade = False
    software_url: str | None = None
    target_parts: list[str] = []
    for token in tokens:
        if token == "-y":
            yes_flag = True
            continue
        if token in {"--allow-downgrade", "--allow_downgrade"}:
            allow_downgrade = True
            continue
        if "://" in token:
            software_url = token
            continue
        target_parts.append(token)
    target = target_parts[0] if target_parts else ""
    return target, yes_flag, software_url, allow_downgrade, ios_software_dir


def confirm_upgrade(
    software_url: str, hosts: list[str], ios_software_dir: str = ""
) -> bool:
    """Prompt the operator to confirm an upgrade action.

    Parameters:
        software_url (str): Software base URL that will be used.
        hosts (list[str]): Hosts that will be targeted.
        ios_software_dir (str): Local directory the images are selected from.

    Returns:
        bool: True when the operator confirms with y/yes.
    """
    host_count = len(hosts)
    host_label = hosts[0] if host_count == 1 else f"{host_count} hosts"
    directory_line = ""
    server_hint = (
        'You can start a local HTTP server with "python3 http-server.py" from the '
        "ios-software directory.\n"
    )
    if ios_software_dir:
        directory_line = f"Local images will be selected from:\n  {ios_software_dir}\n"
        server_hint = (
            'You can start a local HTTP server with "python3 http-server.py" from:\n'
            f"  {ios_software_dir}\n"
        )
    print(
        f"About to potentially upgrade IOS software on {host_label} using images served from:\n"
        f"  {normalize_software_url(software_url)}\n"
        f"{directory_line}"
        "The URL must serve files from the ios-software directory on this host.\n"
        f"{server_hint}"
    )
    answer = input("Proceed with the upgrade? [y/n]: ").strip().lower()
    return answer in {"y", "yes"}


def session_info_for_host(
    host: str,
    ios_username: str,
    ios_password: str,
    ios_port: int,
    ios_secret: str,
) -> dict[str, str | int]:
    return {
        "device_type": "cisco_xe",
        "host": host,
        "username": ios_username,
        "password": ios_password,
        "port": ios_port,
        "secret": ios_secret,
    }


def write_upgrade_command(net_connect: object, command: str) -> None:
    """Write a command or prompt reply to the SSH channel.

    Parameters:
        net_connect (object): Active netmiko connection.
        command (str): Command or prompt reply to send.
    """
    normalized = net_connect.normalize_cmd(command)  # type: ignore[attr-defined]
    net_connect.write_channel(normalized)  # type: ignore[attr-defined]


def read_until_quiet(
    net_connect: object,
    *,
    deadline: float,
    quiet_seconds: float = UPGRADE_READ_QUIET_SECONDS,
) -> str:
    """Read channel data until it stays quiet or the deadline passes.

    Reads the raw channel directly so long-running install output is never
    discarded by netmiko's absolute read timer.

    Parameters:
        net_connect (object): Active netmiko connection.
        deadline (float): time.monotonic() value at which to stop reading.
        quiet_seconds (float): Silence required before returning.

    Returns:
        str: Newly captured output, possibly empty.
    """
    data = ""
    last_chunk_at = time.monotonic()
    while time.monotonic() < deadline:
        chunk = str(net_connect.read_channel())  # type: ignore[attr-defined]
        if chunk:
            data += chunk
            last_chunk_at = time.monotonic()
            continue
        if time.monotonic() - last_chunk_at >= quiet_seconds:
            break
        time.sleep(0.2)
    return data


def copy_transfer_succeeded(output: str) -> bool:
    """Return True when copy output indicates the file landed on flash.

    Parameters:
        output (str): Combined output from the copy command and prompts.

    Returns:
        bool: True when a bytes-copied confirmation is present.
    """
    return bool(re.search(r"bytes copied", output, re.IGNORECASE))


def copy_transfer_failed(output: str) -> str:
    """Extract a copy failure reason from IOS output, if any.

    Parameters:
        output (str): Combined output from the copy command and prompts.

    Returns:
        str: Failure reason, or empty string when none is detected.
    """
    error_match = re.search(
        r"%Error[^\n]*|Error\s*(opening|reading|writing)[^\n]*|"
        r"No such file[^\n]*|Permission denied[^\n]*|"
        r"Connection timed out[^\n]*|Connection refused[^\n]*",
        output,
        re.IGNORECASE,
    )
    if error_match:
        return error_match.group(0).strip()
    return ""


def install_operation_error(output: str) -> str:
    """Extract the most recent IOS install operation error line, if any.

    The %INSTALL-3-OPERATION_ERROR_MESSAGE syslog message is not echoed to an
    SSH session by default, so this also parses 'show logging' output.

    Parameters:
        output (str): Install command output or 'show logging' output.

    Returns:
        str: The full line containing the install error, or empty string.
    """
    matches = re.findall(
        r"[^\r\n]*%INSTALL-3-OPERATION_ERROR_MESSAGE[^\r\n]*",
        output,
    )
    if not matches:
        return ""
    return matches[-1].strip()


def install_staged_target_version(output: str, target_version: str) -> bool:
    """Return True when 'show install summary' lists the target version.

    Parameters:
        output (str): Output of 'show install summary'.
        target_version (str): Version extracted from the image filename.

    Returns:
        bool: True when the target image is staged on the switch.
    """
    if not target_version:
        return False
    return target_version in output


def pending_upgrade_prompt(output: str) -> str | None:
    """Detect an interactive IOS prompt that needs a reply.

    Parameters:
        output (str): Output captured so far for the current command.

    Returns:
        str | None: Reply to send ('y' or newline), or None when no prompt.
    """
    stripped = output.rstrip()
    if not stripped:
        return None
    last_line = stripped.splitlines()[-1].strip().lower()
    if "destination filename" in last_line:
        return "\n"
    if "[confirm]" in last_line:
        return "\n"
    if "over write" in last_line:
        return "\n"
    if "do you want to remove the above files?" in last_line:
        return "y"
    if "[y/n]" in last_line and "remove" in stripped.lower()[-500:]:
        return "y"
    return None


def at_device_prompt(output: str, base_prompt: str = "") -> bool:
    """Return True when output ends at the switch CLI prompt.

    Parameters:
        output (str): Output captured so far for the current command.
        base_prompt (str): Device prompt without the trailing '#' or '>'.

    Returns:
        bool: True when the command has returned to the CLI prompt.
    """
    stripped = output.rstrip()
    if not stripped:
        return False
    last_line = stripped.splitlines()[-1].strip()
    if not last_line.endswith(("#", ">")):
        return False
    if base_prompt and last_line.startswith(base_prompt):
        return True
    return bool(re.fullmatch(r"[\w.\-]+(\([\w.\-]+\))?[#>]", last_line))


def send_upgrade_operation(
    net_connect: object,
    command: str,
    command_log: list[str],
    on_command: Callable[[str], None] | None,
    *,
    read_timeout: int = UPGRADE_COMMAND_TIMEOUT_SECONDS,
    max_idle_seconds: int = UPGRADE_MAX_IDLE_SECONDS,
    done_when: Callable[[str], bool] | None = None,
) -> str:
    """Send a command, answer prompts, and wait for it to finish.

    Parameters:
        net_connect (object): Active netmiko connection.
        command (str): Command to issue.
        command_log (list[str]): Progress/command log to append to.
        on_command (Callable | None): Optional callback for issued text.
        read_timeout (int): Maximum seconds for the whole operation.
        max_idle_seconds (int): Give up after this much silence with no prompt.
        done_when (Callable | None): Optional predicate on captured output
            that ends the wait early when it returns True.

    Returns:
        str: Captured output for the operation.
    """
    report_issued_command(command, command_log, on_command)
    base_prompt = str(getattr(net_connect, "base_prompt", "") or "")
    deadline = time.monotonic() + read_timeout
    # Drop leftover output so a stale prompt cannot end this command early.
    clear_buffer = getattr(net_connect, "clear_buffer", None)
    if callable(clear_buffer):
        clear_buffer()
    write_upgrade_command(net_connect, command)

    combined = ""
    idle_since = time.monotonic()
    while time.monotonic() < deadline:
        current = read_until_quiet(net_connect, deadline=deadline)
        if current:
            combined += current
            idle_since = time.monotonic()

        if done_when is not None and done_when(combined):
            break
        if copy_transfer_failed(combined):
            break

        reply = pending_upgrade_prompt(combined)
        if reply is not None:
            report_issued_command(reply, command_log, on_command)
            write_upgrade_command(net_connect, reply)
            idle_since = time.monotonic()
            continue

        if at_device_prompt(combined, base_prompt):
            break
        if current:
            continue
        if not net_connect.is_alive():  # type: ignore[attr-defined]
            break
        if time.monotonic() - idle_since >= max_idle_seconds:
            logger.warning(
                "No output for %s seconds while running '%s'",
                max_idle_seconds,
                command,
            )
            break

    return combined


def format_issued_command(command: str) -> str:
    """Format a switch command or prompt reply for progress reporting.

    Parameters:
        command (str): Exact string sent to the switch.

    Returns:
        str: Display form of the command.
    """
    if command == "\n":
        return "<enter>"
    return command


def report_issued_command(
    command: str,
    command_log: list[str],
    on_command: Callable[[str], None] | None,
) -> None:
    """Record and optionally report a command about to be issued.

    Quiet routine commands are still logged but not sent to on_command.
    """
    display = format_issued_command(command)
    command_log.append(display)
    if on_command is not None and display not in QUIET_ISSUED_COMMANDS:
        on_command(display)


def report_status(
    message: str,
    command_log: list[str],
    on_status: Callable[[str], None] | None,
) -> None:
    """Record and optionally report a status/progress message."""
    command_log.append(f"{COMMAND_LOG_STATUS_PREFIX}{message}")
    if on_status is not None:
        on_status(message)


def wait_for_host_unreachable(
    host: str,
    *,
    timeout_seconds: int = UPGRADE_REBOOT_DOWN_TIMEOUT_SECONDS,
    poll_seconds: int = UPGRADE_REBOOT_POLL_SECONDS,
) -> bool:
    """Wait until the host stops answering ping (reboot underway).

    Parameters:
        host (str): Hostname or IP address.
        timeout_seconds (int): Maximum time to wait.
        poll_seconds (int): Seconds between ping attempts.

    Returns:
        bool: True when the host becomes unreachable within the timeout.
    """
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not Ping(host, quiet=True):
            return True
        time.sleep(poll_seconds)
    return False


def wait_for_host_reachable(
    host: str,
    *,
    timeout_seconds: int = UPGRADE_REBOOT_UP_TIMEOUT_SECONDS,
    poll_seconds: int = UPGRADE_REBOOT_POLL_SECONDS,
) -> bool:
    """Wait until the host answers ping again after reboot.

    Parameters:
        host (str): Hostname or IP address.
        timeout_seconds (int): Maximum time to wait.
        poll_seconds (int): Seconds between ping attempts.

    Returns:
        bool: True when the host becomes reachable within the timeout.
    """
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if Ping(host, quiet=True):
            return True
        time.sleep(poll_seconds)
    return False


def wait_for_ssh_session(
    host: str,
    ios_username: str,
    ios_password: str,
    ios_port: int,
    ios_secret: str,
    *,
    timeout_seconds: int = UPGRADE_SSH_READY_TIMEOUT_SECONDS,
    poll_seconds: int = UPGRADE_REBOOT_POLL_SECONDS,
) -> object | None:
    """Wait until SSH/enable succeeds after reboot.

    Parameters:
        host (str): Hostname or IP address.
        ios_username (str): SSH username.
        ios_password (str): SSH password.
        ios_port (int): SSH port.
        ios_secret (str): Enable secret.
        timeout_seconds (int): Maximum time to wait for SSH.
        poll_seconds (int): Seconds between connection attempts.

    Returns:
        object | None: Connected netmiko session, or None on timeout.
    """
    deadline = time.monotonic() + timeout_seconds
    session_info = session_info_for_host(
        host, ios_username, ios_password, ios_port, ios_secret
    )
    while time.monotonic() < deadline:
        net_connect = None
        try:
            net_connect = ConnectHandler(**session_info)
            net_connect.enable()
            return net_connect
        except (
            AuthenticationException,
            NetmikoTimeoutException,
            ConnectionException,
            OSError,
            EOFError,
            SSHException,
        ):
            if net_connect is not None:
                try:
                    net_connect.disconnect()
                except Exception:
                    pass
            time.sleep(poll_seconds)
    return None


def wait_for_reboot_and_verify(
    host: str,
    ios_username: str,
    ios_password: str,
    ios_port: int,
    ios_secret: str,
    target_version: str,
    command_log: list[str],
    on_status: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Wait for reboot completion and verify the running IOS version.

    Parameters:
        host (str): Hostname or IP address.
        ios_username (str): SSH username.
        ios_password (str): SSH password.
        ios_port (int): SSH port.
        ios_secret (str): Enable secret.
        target_version (str): Expected version from the image filename.
        command_log (list[str]): Progress/command log to append to.
        on_status (Callable | None): Optional status callback.

    Returns:
        tuple[bool, str]: (success, message_or_new_version).
    """
    report_status(
        "Waiting for switch to go offline (reboot)...",
        command_log,
        on_status,
    )
    if not wait_for_host_unreachable(host):
        return (
            False,
            "Switch did not go offline after install within "
            f"{UPGRADE_REBOOT_DOWN_TIMEOUT_SECONDS} seconds",
        )

    report_status(
        "Switch offline; waiting for it to return...",
        command_log,
        on_status,
    )
    if not wait_for_host_reachable(host):
        return (
            False,
            "Switch did not come back online within "
            f"{UPGRADE_REBOOT_UP_TIMEOUT_SECONDS} seconds",
        )

    report_status(
        "Switch is reachable; waiting for SSH...",
        command_log,
        on_status,
    )
    net_connect = wait_for_ssh_session(
        host, ios_username, ios_password, ios_port, ios_secret
    )
    if net_connect is None:
        return (
            False,
            "Switch came back online but SSH did not become ready within "
            f"{UPGRADE_SSH_READY_TIMEOUT_SECONDS} seconds",
        )

    try:
        show_version_output = str(net_connect.send_command("show version"))
        current_versions = parse_ios_version(show_version_output)
        current_version = format_current_versions(current_versions)
        if not stack_already_on_target(current_versions, target_version):
            return (
                False,
                f"Switch rebooted but running IOS {current_version}, "
                f"expected {target_version}",
            )
        report_status(
            f"Verified running IOS {current_version} after reboot",
            command_log,
            on_status,
        )
        return True, current_version
    finally:
        try:
            net_connect.disconnect()
        except Exception:
            logger.debug("Ignoring disconnect after post-reboot verify on %s", host)


def run_upgrade_commands(
    net_connect: object,
    copy_source: str,
    bin_filename: str,
    command_log: list[str],
    on_command: Callable[[str], None] | None = None,
) -> None:
    """Issue the IOS upgrade command sequence on an open session.

    Parameters:
        net_connect (object): Active netmiko connection.
        copy_source (str): Full source URL/path for the .bin image.
        bin_filename (str): Image basename on flash.
        command_log (list[str]): Progress/command log to append to.
        on_command (Callable | None): Optional callback for issued commands.

    Raises:
        RuntimeError: When the image copy fails or does not complete.
    """
    send_upgrade_operation(
        net_connect,
        "install remove inactive",
        command_log,
        on_command,
    )

    copy_combined = send_upgrade_operation(
        net_connect,
        f"copy {copy_source} flash:",
        command_log,
        on_command,
        done_when=copy_transfer_succeeded,
    )
    copy_error = copy_transfer_failed(copy_combined)
    if copy_error:
        raise RuntimeError(f"Image copy failed: {copy_error}")
    if not copy_transfer_succeeded(copy_combined):
        raise RuntimeError(
            "Image copy did not complete (no 'bytes copied' confirmation). "
            "The transfer may still have been in progress or was interrupted."
        )

    for command in (
        "conf t",
        "no boot system",
        "boot system flash:packages.conf",
        "no boot manual",
        "end",
        "wr mem",
    ):
        send_upgrade_operation(
            net_connect,
            command,
            command_log,
            on_command,
            read_timeout=UPGRADE_CONFIG_COMMAND_TIMEOUT_SECONDS,
            max_idle_seconds=UPGRADE_CONFIG_COMMAND_TIMEOUT_SECONDS,
        )

    install_cmd = (
        f"install add file flash:{bin_filename} activate commit prompt-level none"
    )
    install_output = ""
    try:
        install_output = send_upgrade_operation(
            net_connect,
            install_cmd,
            command_log,
            on_command,
            done_when=lambda output: bool(install_operation_error(output)),
        )
    except (OSError, EOFError, SSHException, ConnectionException, NetmikoTimeoutException):
        # Reboot commonly drops the SSH session after install activate/commit.
        logger.info("SSH session ended after install on switch (likely reboot).")
        return

    install_error = install_operation_error(install_output)
    if install_error:
        raise RuntimeError(f"Install failed: {install_error}")

    verify_install_activated(
        net_connect,
        version_from_bin_filename(bin_filename),
        command_log,
        on_command,
    )


def verify_install_activated(
    net_connect: object,
    target_version: str,
    command_log: list[str],
    on_command: Callable[[str], None] | None = None,
) -> None:
    """Confirm the install staged the new image, or raise with the reason.

    The switch reboots on a successful install, so this only runs when the
    session is still usable. If the session drops while checking (including
    during 'show logging'), or a verify command goes idle without returning to
    the CLI prompt, treat that as a reboot in progress—not a failure. A hung
    TCP session can still report is_alive() during reboot, so missing the
    prompt is the reliable signal.
    %INSTALL-3-OPERATION_ERROR_MESSAGE is read from the logging buffer because
    IOS does not echo syslog to an SSH session.

    Parameters:
        net_connect (object): Active netmiko connection.
        target_version (str): Version extracted from the image filename.
        command_log (list[str]): Progress/command log to append to.
        on_command (Callable | None): Optional callback for issued commands.

    Raises:
        RuntimeError: When the target image was not staged for reboot.
    """
    if not net_connect.is_alive():  # type: ignore[attr-defined]
        return

    base_prompt = str(getattr(net_connect, "base_prompt", "") or "")

    try:
        summary_output = send_upgrade_operation(
            net_connect,
            "show install summary",
            command_log,
            on_command,
            read_timeout=UPGRADE_CONFIG_COMMAND_TIMEOUT_SECONDS,
            max_idle_seconds=UPGRADE_CONFIG_COMMAND_TIMEOUT_SECONDS,
        )
    except (
        OSError,
        EOFError,
        SSHException,
        ConnectionException,
        NetmikoTimeoutException,
    ):
        logger.info(
            "SSH session ended while checking install summary (likely reboot)."
        )
        return

    if not net_connect.is_alive():  # type: ignore[attr-defined]
        logger.info(
            "SSH session dropped after show install summary (likely reboot)."
        )
        return

    if install_staged_target_version(summary_output, target_version):
        return

    # Idle timeout during reboot returns without raising and without a prompt.
    if not at_device_prompt(summary_output, base_prompt):
        logger.info(
            "No CLI prompt after show install summary (likely reboot)."
        )
        return

    try:
        log_output = send_upgrade_operation(
            net_connect,
            "show logging | include INSTALL-3-OPERATION_ERROR_MESSAGE",
            command_log,
            on_command,
            read_timeout=UPGRADE_CONFIG_COMMAND_TIMEOUT_SECONDS,
            max_idle_seconds=UPGRADE_CONFIG_COMMAND_TIMEOUT_SECONDS,
        )
    except (
        OSError,
        EOFError,
        SSHException,
        ConnectionException,
        NetmikoTimeoutException,
    ):
        logger.info(
            "SSH session ended while checking install error log (likely reboot)."
        )
        return

    install_error = install_operation_error(log_output)
    if install_error:
        raise RuntimeError(f"Install failed: {install_error}")

    if not net_connect.is_alive():  # type: ignore[attr-defined]
        logger.info(
            "SSH session dropped after show logging install check (likely reboot)."
        )
        return

    # Same hung-session case as above: silence ends the read loop, TCP may
    # still look alive, but we never got back to the CLI prompt.
    if not at_device_prompt(log_output, base_prompt):
        logger.info(
            "No CLI prompt after show logging install check (likely reboot)."
        )
        return

    raise RuntimeError(
        f"Install did not stage IOS {target_version} and the switch did not "
        "reboot; check 'show install summary' and 'show logging' on the switch"
    )



def upgrade_host(
    host: str,
    software_url: str,
    ios_username: str,
    ios_password: str,
    ios_port: int,
    ios_secret: str,
    *,
    dry_run: bool = False,
    quiet_ping: bool = False,
    allow_downgrade: bool = False,
    ios_software_dir: str | None = None,
    software_preflight_done: bool = False,
    on_command: Callable[[str], None] | None = None,
    on_status: Callable[[str], None] | None = None,
) -> UpgradeResult:
    """Connect to a host and upgrade (or report) IOS software.

    Parameters:
        host (str): FQDN or IP address.
        software_url (str): Base URL serving the ios-software tree.
        ios_username (str): SSH username.
        ios_password (str): SSH password.
        ios_port (int): SSH port.
        ios_secret (str): Enable secret.
        dry_run (bool): When True, connect and report only; do not upgrade.
        quiet_ping (bool): Suppress ping console output.
        allow_downgrade (bool): When True, replace IOS whenever the running
            version is not equal to the served image version.
        ios_software_dir (str | None): Local image directory. When omitted,
            the default ios-software location is used.
        software_preflight_done (bool): When True, skip the HTTP server and
            directory-layout check because the caller already ran it.
        on_command (Callable | None): Optional callback invoked with each
            command string as it is issued to the switch.
        on_status (Callable | None): Optional callback for reboot/progress status.

    Returns:
        UpgradeResult: Per-host outcome.
    """
    command_log: list[str] = []
    if not software_preflight_done:
        preflight_error = preflight_software_server(software_url, ios_software_dir)
        if preflight_error:
            return UpgradeResult(
                host=host,
                status=UpgradeStatus.FAILURE,
                message=preflight_error,
            )
    if not Ping(host, quiet=quiet_ping):
        return UpgradeResult(
            host=host,
            status=UpgradeStatus.FAILURE,
            message="Unable to ping",
        )

    try:
        resolved_ios_software_dir = resolve_ios_software_dir(ios_software_dir)
    except FileNotFoundError as exc:
        return UpgradeResult(
            host=host,
            status=UpgradeStatus.FAILURE,
            message=str(exc),
        )

    session_info = session_info_for_host(
        host, ios_username, ios_password, ios_port, ios_secret
    )
    net_connect = None
    try:
        net_connect = ConnectHandler(**session_info)
        net_connect.enable()
        model = get_switch_model(net_connect)
        show_version_output = str(net_connect.send_command("show version"))
        current_versions = parse_ios_version(show_version_output)
        current_version = format_current_versions(current_versions)
        support = check_minimum_ios_version(model, "0.0.0")
        if support.reason in {"unsupported_model", "unknown_model"}:
            model_label = model if model else "unknown"
            return UpgradeResult(
                host=host,
                status=UpgradeStatus.NOT_SUPPORTED,
                message=(
                    f"Switch model {model_label} is not supported "
                    f"(current IOS {current_version})"
                ),
                model=model_label,
                current_version=current_version,
            )

        sw_name_prefix = get_sw_name_prefix(model)
        if not sw_name_prefix:
            return UpgradeResult(
                host=host,
                status=UpgradeStatus.FAILURE,
                message=(
                    f"No sw_name_prefix for model {model} "
                    f"(current IOS {current_version})"
                ),
                model=model,
                current_version=current_version,
            )

        try:
            bin_filename = resolve_bin_filename(sw_name_prefix, resolved_ios_software_dir)
        except (ValueError, FileNotFoundError) as exc:
            return UpgradeResult(
                host=host,
                status=UpgradeStatus.FAILURE,
                message=f"{exc} (current IOS {current_version})",
                model=model,
                current_version=current_version,
            )

        target_version = version_from_bin_filename(bin_filename)
        version_change = classify_version_change(current_versions, target_version)
        if version_change == "current":
            return UpgradeResult(
                host=host,
                status=UpgradeStatus.ALREADY_CURRENT,
                message=(
                    f"Model {model} already running IOS {current_version} "
                    f"({bin_filename})"
                ),
                model=model,
                image=bin_filename,
                current_version=current_version,
            )

        if version_change in {"downgrade", "mixed"} and not allow_downgrade:
            action = (
                "downgrade"
                if version_change == "downgrade"
                else "mixed upgrade/downgrade"
            )
            return UpgradeResult(
                host=host,
                status=UpgradeStatus.DOWNGRADE_BLOCKED,
                message=(
                    f"Model {model} running IOS {current_version}; served image "
                    f"is {target_version} ({bin_filename}). Refusing {action}; "
                    "re-run with --allow-downgrade to replace when versions differ"
                ),
                model=model,
                image=bin_filename,
                current_version=current_version,
            )

        copy_source = build_copy_source(software_url, sw_name_prefix, bin_filename)
        if version_change == "downgrade":
            action_verb = "downgrade"
        elif version_change == "mixed":
            action_verb = "replace"
        else:
            action_verb = "upgrade"

        if dry_run:
            if version_change == "downgrade":
                dry_run_status = UpgradeStatus.WOULD_DOWNGRADE
            else:
                dry_run_status = UpgradeStatus.WOULD_UPGRADE
            return UpgradeResult(
                host=host,
                status=dry_run_status,
                message=(
                    f"Would {action_verb} model {model} from IOS {current_version} "
                    f"using {bin_filename}"
                ),
                model=model,
                image=bin_filename,
                current_version=current_version,
            )

        progress_labels = {
            "upgrade": "UPGRADING",
            "downgrade": "DOWNGRADING",
            "replace": "REPLACING",
        }
        report_status(
            f"{progress_labels[action_verb]} model {model} from IOS "
            f"{current_version} using {bin_filename}",
            command_log,
            on_status,
        )
        run_upgrade_commands(
            net_connect,
            copy_source,
            bin_filename,
            command_log,
            on_command=on_command,
        )
        try:
            net_connect.disconnect()
        except Exception:
            logger.debug("Ignoring disconnect before reboot wait on %s", host)
        net_connect = None

        reboot_ok, reboot_detail = wait_for_reboot_and_verify(
            host,
            ios_username,
            ios_password,
            ios_port,
            ios_secret,
            target_version,
            command_log,
            on_status=on_status,
        )
        if not reboot_ok:
            return UpgradeResult(
                host=host,
                status=UpgradeStatus.FAILURE,
                message=reboot_detail,
                model=model,
                image=bin_filename,
                current_version=current_version,
                command_log=tuple(command_log),
            )

        return UpgradeResult(
            host=host,
            status=UpgradeStatus.SUCCESS,
            message=(
                f"{action_verb.capitalize()}d from IOS {current_version} to "
                f"{reboot_detail} using {bin_filename}"
            ),
            model=model,
            image=bin_filename,
            current_version=reboot_detail,
            command_log=tuple(command_log),
        )
    except AuthenticationException:
        return UpgradeResult(
            host=host,
            status=UpgradeStatus.FAILURE,
            message="SSH authentication failed",
            command_log=tuple(command_log),
        )
    except NetmikoTimeoutException as exc:
        return UpgradeResult(
            host=host,
            status=UpgradeStatus.FAILURE,
            message=f"SSH connection timed out: {exc}",
            command_log=tuple(command_log),
        )
    except ConnectionException as exc:
        return UpgradeResult(
            host=host,
            status=UpgradeStatus.FAILURE,
            message=f"SSH connection failed: {exc}",
            command_log=tuple(command_log),
        )
    except (OSError, EOFError, SSHException) as exc:
        # If we already started install, reboot may surface here; treat as
        # connection-level failure when we never reached a clean success return.
        return UpgradeResult(
            host=host,
            status=UpgradeStatus.FAILURE,
            message=f"SSH session error: {exc}",
            command_log=tuple(command_log),
        )
    except RuntimeError as exc:
        return UpgradeResult(
            host=host,
            status=UpgradeStatus.FAILURE,
            message=str(exc),
            command_log=tuple(command_log),
        )
    except Exception as exc:
        return UpgradeResult(
            host=host,
            status=UpgradeStatus.FAILURE,
            message=f"error: {exc}",
            command_log=tuple(command_log),
        )
    finally:
        if net_connect is not None:
            try:
                net_connect.disconnect()
            except Exception:
                logger.debug("Ignoring disconnect error after upgrade on %s", host)


def format_upgrade_result_line(result: UpgradeResult) -> str:
    """Format a one-line summary for an upgrade result.

    Parameters:
        result (UpgradeResult): Per-host result.

    Returns:
        str: Single-line status suitable for console streaming.
    """
    # IPv4 addresses are at most 15 characters (e.g. 255.255.255.255),
    # so left-align "<ip>: " to 17 columns before the status text.
    host_prefix = f"{result.host}: "
    aligned_prefix = f"{host_prefix:<17}"
    if result.status == UpgradeStatus.SUCCESS:
        detail = f"SUCCESS - {result.message}"
    elif result.status == UpgradeStatus.WOULD_UPGRADE:
        detail = f"WOULD UPGRADE - {result.message}"
    elif result.status == UpgradeStatus.WOULD_DOWNGRADE:
        detail = f"WOULD DOWNGRADE - {result.message}"
    elif result.status == UpgradeStatus.ALREADY_CURRENT:
        detail = f"ALREADY CURRENT - {result.message}"
    elif result.status == UpgradeStatus.DOWNGRADE_BLOCKED:
        detail = f"DOWNGRADE BLOCKED - {result.message}"
    elif result.status == UpgradeStatus.NOT_SUPPORTED:
        detail = f"NOT SUPPORTED - {result.message}"
    else:
        detail = f"FAILURE - {result.message}"
    return f"{aligned_prefix}{detail}\n"


def format_upgrade_command_log_lines(result: UpgradeResult) -> str:
    """Format issued-command lines for a host, suitable for log files.

    Parameters:
        result (UpgradeResult): Per-host result including command_log.

    Returns:
        str: Host-prefixed Issuing/status lines, or empty string when none.
    """
    if not result.command_log:
        return ""
    host_prefix = f"{result.host}: "
    aligned_prefix = f"{host_prefix:<17}"
    lines: list[str] = []
    for entry in result.command_log:
        if entry.startswith(COMMAND_LOG_STATUS_PREFIX):
            message = entry[len(COMMAND_LOG_STATUS_PREFIX) :]
            lines.append(f"{aligned_prefix}{message}\n")
        else:
            lines.append(f"{aligned_prefix}Issuing: {entry}\n")
    return "".join(lines)


def format_upgrade_summary(results: list[UpgradeResult]) -> str:
    """Build a report of per-host upgrade results.

    Parameters:
        results (list[UpgradeResult]): All per-host results.

    Returns:
        str: One result line per host.
    """
    return "".join(format_upgrade_result_line(result) for result in results)


def upgrade_hosts(
    hosts: list[str],
    software_url: str,
    ios_username: str,
    ios_password: str,
    ios_port: int,
    ios_secret: str,
    *,
    dry_run: bool = False,
    allow_downgrade: bool = False,
    ios_software_dir: str | None = None,
    on_complete: Callable[[UpgradeResult], None] | None = None,
    on_status: Callable[[str, str], None] | None = None,
    on_command: Callable[[str, str], None] | None = None,
    max_workers: int = DEFAULT_PARALLEL_MAX_WORKERS,
) -> list[UpgradeResult]:
    """Upgrade multiple hosts in parallel.

    Parameters:
        hosts (list[str]): Hostnames or IP addresses.
        software_url (str): Base URL serving ios-software.
        ios_username (str): SSH username.
        ios_password (str): SSH password.
        ios_port (int): SSH port.
        ios_secret (str): Enable secret.
        dry_run (bool): When True, probe only.
        allow_downgrade (bool): When True, replace when versions differ.
        ios_software_dir (str | None): Local image directory. When omitted,
            the default ios-software location is used.
        on_complete (Callable | None): Optional callback as each host finishes.
        on_status (Callable | None): Optional callback(host, message) for
            in-progress status such as UPGRADING/DOWNGRADING.
        on_command (Callable | None): Optional callback(host, command) for
            each command issued to a switch.
        max_workers (int): Parallel worker limit.

    Returns:
        list[UpgradeResult]: Results in the same order as hosts. When the
        software HTTP server is unavailable or the image layout is invalid,
        every host is reported as a failure and no switch is contacted.
    """
    normalized_url = normalize_software_url(software_url)
    preflight_error = preflight_software_server(normalized_url, ios_software_dir)
    if preflight_error:
        return [
            UpgradeResult(
                host=hostname,
                status=UpgradeStatus.FAILURE,
                message=preflight_error,
            )
            for hostname in hosts
        ]

    def worker(index: int, hostname: str) -> UpgradeResult:
        def host_status(message: str) -> None:
            if on_status is not None:
                on_status(hostname, message)

        def host_command(command: str) -> None:
            if on_command is not None:
                on_command(hostname, command)

        return upgrade_host(
            hostname,
            normalized_url,
            ios_username,
            ios_password,
            ios_port,
            ios_secret,
            dry_run=dry_run,
            quiet_ping=True,
            allow_downgrade=allow_downgrade,
            ios_software_dir=ios_software_dir,
            software_preflight_done=True,
            on_status=host_status if on_status is not None else None,
            on_command=host_command if on_command is not None else None,
        )

    return run_parallel_indexed(
        hosts,
        worker,
        max_workers=max_workers,
        on_complete=on_complete,
    )
