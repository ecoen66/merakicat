#!/usr/bin/env python3

# This is a simple multi-threaded HTTP server that can be used to serve files
# such as IOS firmware.
import sys

# Don't litter the directory with __pycache__ files
sys.dont_write_bytecode = True


import argparse
import os
import socket
import subprocess
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import BinaryIO

TRANSFER_CHUNK_SIZE = 64 * 1024
PROGRESS_PERCENT_STEP = 1
MAX_CONCURRENT_CONNECTIONS = 20


class Handler(SimpleHTTPRequestHandler):
    def setup(self) -> None:
        super().setup()
        print(f"CONNECT {self.client_address[0]}:{self.client_address[1]}")

    def finish(self) -> None:
        print(f"DISCONNECT {self.client_address[0]}:{self.client_address[1]}")
        super().finish()

    def log_message(self, format: str, *args) -> None:  
        """Suppress the default BaseHTTPRequestHandler request log line."""
        return

    def do_GET(self) -> None:
        client = f"{self.client_address[0]}:{self.client_address[1]}"
        print(f"GET {self.path} from {client}")
        try:
            super().do_GET()
        except (BrokenPipeError, ConnectionResetError, TimeoutError) as exc:
            print(f"  TRANSFER ABORTED {self.path} to {client}: {exc}")

    def copyfile(self, source: BinaryIO, outputfile: BinaryIO) -> None:
        """Copy a file to the client while reporting transfer progress."""
        client = f"{self.client_address[0]}:{self.client_address[1]}"
        path = self.path
        size: int | None
        try:
            size = os.fstat(source.fileno()).st_size
        except (AttributeError, OSError, ValueError):
            size = None

        if size is not None:
            print(f"  TRANSFER START {path} to {client}: {size} bytes")
        else:
            print(f"  TRANSFER START {path} to {client}: size unknown")

        bytes_sent = 0
        last_reported_pct = -PROGRESS_PERCENT_STEP
        try:
            while True:
                buffer = source.read(TRANSFER_CHUNK_SIZE)
                if not buffer:
                    break
                outputfile.write(buffer)
                bytes_sent += len(buffer)
                if size and size > 0:
                    percent = int((100 * bytes_sent) / size)
                    if (
                        percent >= last_reported_pct + PROGRESS_PERCENT_STEP
                        or bytes_sent >= size
                    ):
                        print(
                            f"  TRANSFER {path} to {client}: "
                            f"{bytes_sent}/{size} bytes ({percent}%)"
                        )
                        last_reported_pct = percent
            print(
                f"  TRANSFER COMPLETE {path} to {client}: {bytes_sent} bytes"
            )
        except (BrokenPipeError, ConnectionResetError, TimeoutError) as exc:
            detail = f"{bytes_sent}"
            if size is not None:
                detail = f"{bytes_sent}/{size}"
            print(
                f"  TRANSFER FAILED {path} to {client}: "
                f"{detail} bytes sent ({exc})"
            )
            raise


class QuietThreadingHTTPServer(ThreadingHTTPServer):
    """Threading HTTP server capped at MAX_CONCURRENT_CONNECTIONS workers."""

    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[SimpleHTTPRequestHandler],
    ) -> None:
        self.executor = ThreadPoolExecutor(
            max_workers=MAX_CONCURRENT_CONNECTIONS
        )
        super().__init__(server_address, RequestHandlerClass)

    def process_request(
        self,
        request: socket.socket,
        client_address: tuple[str, int],
    ) -> None:
        """Handle each request in a pooled worker thread."""
        self.executor.submit(self.process_request_thread, request, client_address)

    def server_close(self) -> None:
        super().server_close()
        self.executor.shutdown(wait=False)

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


def main() -> None:
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
    print(f"Max concurrent connections: {MAX_CONCURRENT_CONNECTIONS}")
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
