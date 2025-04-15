#!/usr/bin/env python3.12
import asyncio
import signal
import socket
import argparse
import sys
import time

target_ips = []

running = True  # Flag for stopping the server
PORT = None  # Port to listen on, set via argument
udp_socket = None


def log_debug(msg, debug):
    if debug:
        print(msg)


def read_ips_from_config(config_file):
    """
    Read the list of IPs from a config file.
    """
    with open(config_file, "r") as file:
        ips = [line.strip() for line in file if line.strip()]
    return ips


async def forward_data(data, ip, debug):
    """
    Forward data to a target server using UDP.
    """
    try:
        # Create a UDP socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            # Send data to the target server
            udp_socket.sendto(data, (ip, PORT))
            log_debug(f"Data forwarded to {ip}:{PORT}", debug)
    except Exception as e:
        log_debug(f"Failed to forward data to {ip}:{PORT}: {e}", debug)


async def handle_client(udp_socket, debug):
    """
    Handle incoming UDP packets and forward them to all target servers.
    """
    try:
        while running:
            log_debug("Waiting for data...", debug)
            # Receive data from the client (non-blocking)
            loop = asyncio.get_running_loop()
            data, addr = await loop.sock_recvfrom(udp_socket, 4096)
            if not data:
                break  # Exit if no data is received

            log_debug(f"Received data from {addr}: {data.decode()}", debug)

            # Forward data to all targets concurrently
            tasks = [forward_data(data, ip, debug) for ip in target_ips]
            await asyncio.gather(*tasks)  # Run all tasks concurrently
    except Exception as e:
        log_debug(f"Error handling client: {e}", debug)


async def start_server(debug):
    """
    Start the UDP server and handle incoming packets.
    """
    # Create a UDP socket
    global udp_socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("0.0.0.0", PORT))
    udp_socket.setblocking(False)  # Set socket to non-blocking mode
    log_debug(f"Listening on port {PORT}...", debug)

    # Start the client handler
    await handle_client(udp_socket, debug)

    # Clean up
    udp_socket.close()
    log_debug("Server shut down", debug)


def shutdown_server(signum, frame):
    """
    Gracefully shut down the server.
    """
    global running, udp_socket
    running = False
    log_debug("Shutting down server...", True)

    if udp_socket is not None:
        try:
            udp_socket.close()
        except Exception as _:
            log_debug(f"Error closing socket", True)

    loop = asyncio.get_running_loop()
    loop.stop()
    time.sleep(3)
    sys.exit()


def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="UDP Forwarder")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--config", type=str, default="config.txt", help="Path to config file containing IPs")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


async def main():
    """
    Main function to start the UDP server.
    """
    args = parse_args()
    global PORT, target_ips
    PORT = args.port
    target_ips = read_ips_from_config(args.config)

    # Handle shutdown signals
    signal.signal(signal.SIGINT, shutdown_server)

    await start_server(args.debug)


if __name__ == "__main__":
    asyncio.run(main())
