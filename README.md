# TCP/UDP Relay Tool
This project provides Python scripts to relay TCP and UDP packets to multiple destinations. It is useful for scenarios where you need to forward network traffic to multiple test endpoints (e.g., debugging, load testing, or redundancy setups).

## Features
- High-performance packet relaying using Python async
- Supports TCP and UDP protocols
- Configurable via command-line arguments or a config file
- Includes example systemd unit files for easy deployment
- Tested on Linux (should work on Windows as well)

## Requirements
- Python ≥ 3.12
- ncat/nc (for testing)

## Installation
1. Clone or download the scripts to a directory.
2. (Optional) Set up a virtual environment:
    ```
    python -m venv venv  
    source venv/bin/activate  # Linux/macOS  
    venv\Scripts\activate     # Windows  
    ```

## Usage
1. Create a config.txt file (or specify your own path to config file) listing destination IPs:
2. Run the relay with the config file:
    ```
    ./tcprelay.py --port 9000 --config config.txt --debug  
    ```
3. To forward data received in multiple port simply run the script with different `--port` argument

## Testing 
1. Start test listeners on destinations (e.g., using ncat):
    ```
    ncat -l -p 9000 -k  # TCP  
    ncat -l -u -p 5000  # UDP  
    ```
2. Send test messages to the relay:
    ```
    ncat <relay-ip> 9000      # TCP  
    ncat -u <relay-ip> 5000   # UDP  
    ```

## Deployment
### systemd Service (Linux)
Example unit files are included. To run as a service:
1. Modify the example .service files with your paths/args.
2. Copy to /etc/systemd/system/:
    ```
    sudo cp tcprelay.service /etc/systemd/system/  
    sudo systemctl enable tcprelay  
    sudo systemctl start tcprelay 
    ``` 

## Contributing
Feel free to contribute. Open a Pull Request with a clear description of your proposed changes. 