#!/usr/bin/env python3
import asyncio
import signal
import argparse
import sys
import time

target_connections = {}  # Persistent connections to target servers
running = True  # Flag for stopping the server
PORT = None  # Port to listen on, set via argument


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


async def connect_to_targets(debug):
    """
    Establish and maintain persistent connections to target servers.
    Only attempts to connect to IPs with a value of None.
    """
    global target_connections
    tasks = []

    for ip in target_connections:
        if target_connections[ip] is not None:
            continue  # Skip if already connected

        tasks.append(connect_to_target(ip, debug))

    if tasks:
        await asyncio.gather(*tasks)


async def connect_to_target(ip, debug):
    """
    Connect to a single target server and store the connection.
    """
    global target_connections
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, PORT), timeout=5
        )
        target_connections[ip] = (reader, writer)  # Atomic assignment
        log_debug(f"Connected to target server {ip}:{PORT}", debug)
    except Exception as e:
        log_debug(f"Failed to connect to target server {ip}:{PORT}: {e}", debug)


async def reconnect_task(debug):
    """
    Periodically attempt to reconnect to failed targets.
    """
    while running:
        log_debug("> Connection maintenance task...", debug)
        await connect_to_targets(debug)
        await asyncio.sleep(10)


async def forward_data(data, debug):
    """
    Forward data to all target servers with a non-None connection.
    """
    tasks = []
    for ip, conn in target_connections.items():
        if conn is not None:
            tasks.append(forward_to_target(ip, conn, data, debug))

    if tasks:
        await asyncio.gather(*tasks)


async def forward_to_target(ip, conn, data, debug):
    """
    Forward data to a single target server.
    """
    reader, writer = conn
    try:
        writer.write(data)
        await writer.drain()  # Ensure data is sent
        log_debug(f"Data forwarded to {ip}:{PORT}", debug)
    except (ConnectionResetError, BrokenPipeError):
        log_debug(f"Connection to {ip} is closed. Resetting connection.", debug)
        target_connections[ip] = None  # Reset the connection
    except Exception as e:
        log_debug(f"Failed to forward data to {ip}:{PORT}: {e}", debug)


async def handle_client(reader, writer, debug):
    """
    Handle incoming client connections and forward data to target servers.
    """
    try:
        while running:
            data = await reader.read(4096)
            if not data:
                break  # Exit if no data is received

            log_debug(f"Received data from client: {data.decode()}", debug)

            # Forward data to all targets with non-None connections
            await forward_data(data, debug)
    except Exception as e:
        log_debug(f"Error handling client: {e}", debug)
    finally:
        writer.close()
        await writer.wait_closed()
        log_debug("Client connection closed", debug)


async def start_server(debug):
    """
    Start the TCP server and handle incoming connections.
    """
    # Establish initial connections to target servers
    await connect_to_targets(debug)

    # Start the reconnection task
    asyncio.create_task(reconnect_task(debug))

    async def client_connected(reader, writer):
        addr = writer.get_extra_info("peername")
        log_debug(f"New client connected: {addr}", debug)
        await handle_client(reader, writer, debug)

    # Start the TCP server
    server = await asyncio.start_server(
        client_connected,
        "0.0.0.0", PORT
    )
    log_debug(f"Listening on port {PORT}...", debug)

    async with server:
        await server.serve_forever()


def shutdown_server(signum, frame):
    """
    Shut down the server gracefully.
    """
    global running
    running = False
    log_debug("Shutting down server...", True)

    # Close all target connections
    for ip, conn in target_connections.items():
        try:
            if conn is not None:
                _, writer = conn
                writer.close()
                writer.wait_closed()
        except Exception as _:
            log_debug(f"Error closing connection", True)

    loop = asyncio.get_running_loop()
    loop.stop()
    time.sleep(3)
    sys.exit()


def parse_args():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="TCP Forwarder")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--config", type=str, default="config.txt", help="Path to config file containing IPs")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


async def main():
    args = parse_args()
    global PORT, target_connections

    # Read IPs from the config file and initialize target_connections
    ips = read_ips_from_config(args.config)
    target_connections = {ip: None for ip in ips}  # Initialize with None
    PORT = args.port

    # Set up signal handling for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_server)

    # Start the server
    await start_server(args.debug)


if __name__ == "__main__":
    asyncio.run(main())
