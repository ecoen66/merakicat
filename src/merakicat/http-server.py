#!/usr/bin/env python3

# This is a simple multi-threaded HTTP server that can be used to serve files
# such as IOS firmware  

import argparse
import os
import socket
import subprocess
import sys
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class Handler(SimpleHTTPRequestHandler):
    def setup(self):
        super().setup()
        print(f"CONNECT {self.client_address}")

    def finish(self):
        print(f"DISCONNECT {self.client_address}")
        super().finish()


class QuietThreadingHTTPServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):  # noqa: ARG002
        """Ignore noisy disconnect errors; keep other tracebacks."""
        _, exc_value, _ = sys.exc_info()
        if isinstance(exc_value, (BrokenPipeError, ConnectionResetError)):
            return
        traceback.print_exc()


def get_local_ipv4_addresses() -> list[str]:
    """Return all detected local IPv4 addresses."""
    addresses: set[str] = {"127.0.0.1"}

    hostname = socket.gethostname()
    candidate_names = {hostname, socket.getfqdn()}

    for name in candidate_names:
        try:
            info = socket.getaddrinfo(name, None, family=socket.AF_INET)
        except socket.gaierror:
            continue
        for entry in info:
            ip_address = entry[4][0]
            if isinstance(ip_address, str):
                addresses.add(ip_address)

    # Parse interface-level IPv4 addresses (including VPN interfaces).
    try:
        result = subprocess.run(
            ["ifconfig"],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped.startswith("inet "):
                continue
            parts = stripped.split()
            if len(parts) < 2:
                continue
            ip_address = parts[1]
            if ip_address != "127.0.0.1":
                addresses.add(ip_address)
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    # Capture the active outbound interface address when available.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            addresses.add(sock.getsockname()[0])
    except OSError:
        pass

    return sorted(addresses)


def get_bound_ipv4_addresses(bind_host: str) -> list[str]:
    """Resolve the IPv4 addresses this server is listening on."""
    if bind_host == "0.0.0.0":
        return get_local_ipv4_addresses()

    try:
        info = socket.getaddrinfo(bind_host, None, family=socket.AF_INET)
    except socket.gaierror:
        return [bind_host]

    resolved = sorted(
        {
            entry[4][0]
            for entry in info
            if isinstance(entry[4][0], str)
        }
    )
    return resolved or [bind_host]


def main():
    parser = argparse.ArgumentParser(
        description="Multi-threaded HTTP server with optional working directory",
        add_help=False,
    )

    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit",
    )

    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host/IP to bind to (default: 0.0.0.0)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )

    parser.add_argument(
        "--directory",
        default=".",
        help="Directory to serve files from (default: current directory)",
    )
    parser.add_argument(
        "--exit",
        action="store_true",
        help="Bind, print listening addresses, then exit immediately",
    )

    args = parser.parse_args()

    directory = os.path.abspath(args.directory)

    if not os.path.isdir(directory):
        raise SystemExit(f"ERROR: Directory does not exist: {directory}")

    os.chdir(directory)

    server = QuietThreadingHTTPServer(
        (args.host, args.port),
        Handler,
    )

    print(f"Serving directory: {directory}")
    bound_ips = get_bound_ipv4_addresses(args.host)
    print("Listening on:")
    for ip_address in bound_ips:
        print(f"  http://{ip_address}:{args.port}")

    if args.exit:
        server.server_close()
        return

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()