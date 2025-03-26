import socket
import json
import os
import sys
import subprocess
import time
import argparse


def get_ip_address():
    """Get the local machine's IP address"""
    try:
        # Create a socket to connect to an external server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # This doesn't actually create a connection
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception as e:
        print(f"Error getting IP address: {e}")
        return "localhost"  # Fallback to localhost if we can't get IP


def load_server_config():
    """Load server configuration from JSON file"""
    try:
        with open('server_config.json', 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading server config: {e}")
        return None


def check_local_servers():
    """Check which servers in the config are on the current machine"""
    local_ip = get_ip_address()
    config = load_server_config()
    
    if not config:
        return []
        
    local_servers = []
    for server in config:
        if server['host'] == local_ip:
            local_servers.append(server)
            print(f"Found local server: {server['node_id']} on port {server['port']}")
            
    return local_servers


def start_local_servers():
    """Start each local server in a separate terminal window"""
    local_servers = check_local_servers()
    
    if not local_servers:
        print("No local servers found in configuration.")
        return
    
    print(f"Starting {len(local_servers)} local servers in separate terminal windows...")
    
    # Create data directory if it doesn't exist
    os.makedirs("./data", exist_ok=True)
    os.makedirs("./logs", exist_ok=True)
    
    # Get all servers for peer configuration
    all_servers = load_server_config()
    
    for server in local_servers:
        node_id = server['node_id']
        port = server['port']
        db_path = server['database']
        
        # Build the peer list
        peer_args = []
        for peer in all_servers:
            if peer['node_id'] != node_id:
                peer_args.extend(["--peer", f"{peer['node_id']}:{peer['host']}:{peer['port']}"])
        
        # Construct the command to run the server
        cmd = [
            "python3", "src/run_server.py",
            "--node-id", node_id,
            "--port", str(port),
            "--db-path", db_path,
            *peer_args
        ]
        
        # Convert the command to a string for the terminal
        cmd_str = " ".join(cmd)
        
        # Get the current directory to ensure correct path resolution
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        os.chdir(parent_dir)  # Change to the project root directory
        
        # Start the server in a new terminal window based on platform
        if sys.platform == 'darwin':  # macOS
            # Using AppleScript to open a new Terminal window with the command
            apple_script = f'''
                tell application "Terminal"
                    do script "cd '{parent_dir}' && {cmd_str}"
                end tell
            '''
            subprocess.Popen(['osascript', '-e', apple_script])
        elif sys.platform == 'win32':  # Windows
            # Using cmd's start command to open a new command prompt
            subprocess.Popen(f'start cmd /k cd /d "{parent_dir}" && {cmd_str}', shell=True)
        else:  # Linux and other Unix-like systems
            # Try different terminal emulators
            launched = False
            terminals = ['gnome-terminal', 'xterm', 'konsole', 'terminator']
            for terminal in terminals:
                try:
                    if terminal == 'gnome-terminal':
                        subprocess.Popen([terminal, '--', 'bash', '-c', f"cd '{parent_dir}' && {cmd_str}; exec bash"])
                    else:
                        subprocess.Popen([terminal, '-e', f"cd '{parent_dir}' && {cmd_str}"])
                    launched = True
                    break
                except FileNotFoundError:
                    continue
            
            if not launched:
                print(f"Warning: Could not find a terminal emulator to run {node_id}. Please start it manually.")
                print(f"Command: cd {parent_dir} && {cmd_str}")
        
        print(f"Started {node_id} on port {port}")
        time.sleep(1)  # Small delay between starting servers


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Start local chat servers in separate terminal windows")
    args = parser.parse_args()
    
    # Start the servers
    start_local_servers()
