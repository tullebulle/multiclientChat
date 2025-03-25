#!/usr/bin/env python3
"""
Start a cluster of chat servers using multiprocessing
"""

import os
import sys
import time
import signal
import argparse
import subprocess

DATA_DIR = "./data"
LOG_DIR = "./logs"

def run_server(node_id, port, all_servers):
    """Start a single server process"""
    # Build the peer list
    peer_args = []
    for peer_id, peer_port in all_servers.items():
        if peer_id != node_id:
            peer_args.extend(["--peer", f"{peer_id}:localhost:{peer_port}"])
    
    # Log the command being executed
    print(f"Starting {node_id} on port {port} with peers: {peer_args}")
    
    # Create the data directory path
    db_path = f"./data/{node_id}.db"
    
    # Start the server process
    cmd = [
        "python3", "src/run_server.py",
        "--node-id", node_id,
        "--port", str(port),
        "--db-path", db_path,
        *peer_args
    ]
    
    # Redirect output to log file
    log_file = open(f"{LOG_DIR}/{node_id}.log", "w")
    
    # Start the process
    return subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True
    )

def start_cluster():
    """Start a cluster of three servers"""
    print("===== START CLUSTER SCRIPT RUNNING =====")
    print("Current working directory:", os.getcwd())
    print("Starting chat server cluster...")
    
    # Make sure directories exist
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Define the server configuration
    servers = {
        "node1": 9001,
        "node2": 9002,
        "node3": 9003
    }
    
    # Verify server script exists
    server_script = "src/run_server.py"
    if not os.path.isfile(server_script):
        print(f"ERROR: Server script not found: {server_script}")
        print(f"Files in src directory: {os.listdir('src')}")
        return {}
    else:
        print(f"Server script found: {server_script}")
    
    # Start all server processes
    processes = {}
    for node_id, port in servers.items():
        # Start the server
        print(f"\n----- Starting {node_id} -----")
        processes[node_id] = run_server(node_id, port, servers)
        print(f"Started server {node_id} on port {port}, PID: {processes[node_id].pid}")
        
        # Small delay to avoid startup race conditions
        time.sleep(0.5)
    
    # Verify all processes are still running
    print("\nVerifying processes are still running:")
    all_running = True
    for node_id, process in processes.items():
        if process.poll() is None:
            print(f"  {node_id}: Running (PID: {process.pid})")
        else:
            print(f"  {node_id}: TERMINATED with code {process.poll()}")
            all_running = False
    
    if all_running:
        print("\nAll servers started successfully!")
    else:
        print("\nWARNING: Some servers failed to start. Check logs for errors.")
    
    print(f"Check logs in {LOG_DIR}")
    print("")
    print("To connect with the client, run:")
    print("python src/run_gui.py --protocol grpc --server localhost:9001,localhost:9002,localhost:9003")
    
    # Return processes so they can be monitored
    return processes

def stop_cluster():
    """Stop all server processes"""
    print("===== STOP CLUSTER SCRIPT RUNNING =====")
    print("Current working directory:", os.getcwd())
    print("Stopping chat server cluster...")
    
    # Find Python processes running run_server.py
    try:
        print("Finding running server processes...")
        ps_output = subprocess.check_output(["ps", "-ef"]).decode()
        server_processes = []
        
        for line in ps_output.split('\n'):
            if "run_server.py" in line and "python" in line:
                print(f"Found server process: {line}")
                parts = line.split()
                if len(parts) >= 2:
                    pid = int(parts[1])
                    server_processes.append(pid)
        
        process_count = len(server_processes)
        
        if process_count == 0:
            print("No running server processes found.")
            return
        
        print(f"Found {process_count} running server processes.")
        
        # Kill all server processes
        for pid in server_processes:
            try:
                print(f"Sending SIGTERM to process {pid}")
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                print(f"Process {pid} not found")
                pass  # Process already gone
        
        # Wait a moment and check if they're all gone
        print("Waiting for processes to terminate...")
        time.sleep(1)
        
        # Check for remaining processes
        remaining_processes = []
        ps_output = subprocess.check_output(["ps", "-ef"]).decode()
        for line in ps_output.split('\n'):
            if "run_server.py" in line and "python" in line:
                parts = line.split()
                if len(parts) >= 2:
                    pid = int(parts[1])
                    remaining_processes.append(pid)
                    print(f"Process still running: {line}")
        
        if not remaining_processes:
            print(f"Successfully stopped all {process_count} server processes.")
        else:
            remaining_count = len(remaining_processes)
            print(f"Warning: {remaining_count} server processes still running.")
            print("Forcefully terminating remaining processes...")
            
            for pid in remaining_processes:
                try:
                    print(f"Sending SIGKILL to process {pid}")
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    print(f"Process {pid} not found")
                    pass  # Process already gone
            
            print("Done.")
    
    except Exception as e:
        print(f"Error stopping processes: {e}")

def main():
    parser = argparse.ArgumentParser(description="Start or stop a chat server cluster")
    parser.add_argument('action', choices=['start', 'stop'], help='Action to perform')
    
    args = parser.parse_args()
    
    if args.action == 'start':
        processes = start_cluster()
        
        # Keep the main process alive
        try:
            print("Monitoring server processes...")
            # Periodically check if all processes are still running
            while all(p.poll() is None for p in processes.values()):
                time.sleep(1)
                
            # If we get here, at least one process has terminated
            failed_nodes = [node_id for node_id, p in processes.items() if p.poll() is not None]
            print(f"WARNING: Nodes {failed_nodes} have terminated unexpectedly")
            
            # Print exit codes
            for node_id, p in processes.items():
                if p.poll() is not None:
                    print(f"Node {node_id} exit code: {p.poll()}")
                    
                    # Print log if available
                    log_path = f"{LOG_DIR}/{node_id}.log"
                    try:
                        with open(log_path, "r") as f:
                            log_content = f.read()
                            print(f"Log for {node_id}:")
                            print(log_content)
                    except Exception as e:
                        print(f"Error reading log: {e}")
                        
        except KeyboardInterrupt:
            print("\nStopping all servers...")
            stop_cluster()
    
    elif args.action == 'stop':
        stop_cluster()

if __name__ == "__main__":
    main() 