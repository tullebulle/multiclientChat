#!/usr/bin/env python3
"""
Manage nodes in the Raft cluster - kill or revive a specific node to test fault tolerance.
"""

import os
import sys
import time
import signal
import argparse
import subprocess

def find_node_pid(node_id):
    """Find the PID of a specific node"""
    try:
        ps_output = subprocess.check_output(["ps", "-ef"]).decode()
        
        for line in ps_output.split('\n'):
            if "run_server.py" in line and f"--node-id {node_id}" in line and "python" in line:
                parts = line.split()
                if len(parts) >= 2:
                    return int(parts[1])
        
        return None
    except Exception as e:
        print(f"Error finding process: {e}")
        return None

def kill_node(node_id):
    """Kill a specific node in the cluster"""
    pid = find_node_pid(node_id)
    
    if pid:
        print(f"Found {node_id} running with PID {pid}")
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to {node_id} (PID: {pid})")
            
            # Wait to ensure the process is terminated
            time.sleep(1)
            if find_node_pid(node_id) is None:
                print(f"Successfully killed {node_id}")
                return True
            else:
                print(f"Process still running, sending SIGKILL...")
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)
                return find_node_pid(node_id) is None
        except Exception as e:
            print(f"Error killing process: {e}")
            return False
    else:
        print(f"Could not find process for {node_id}")
        return False

def revive_node(node_id):
    """Revive a specific node in the cluster"""
    # Make sure node isn't already running
    if find_node_pid(node_id):
        print(f"{node_id} is already running")
        return False
    
    # Get port for this node
    node_ports = {
        "node1": 9001,
        "node2": 9002,
        "node3": 9003
    }
    
    if node_id not in node_ports:
        print(f"Unknown node ID: {node_id}")
        return False
    
    port = node_ports[node_id]
    
    # Build peer list
    peer_args = []
    for peer_id, peer_port in node_ports.items():
        if peer_id != node_id:
            peer_args.extend(["--peer", f"{peer_id}:localhost:{peer_port}"])
    
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
    
    print(f"Reviving {node_id} with command: {' '.join(cmd)}")
    
    # Redirect output to log file
    log_dir = "./logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = open(f"{log_dir}/{node_id}.log", "w")
    
    # Start the process
    try:
        process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        
        print(f"Started {node_id} with PID: {process.pid}")
        
        # Check if process is still running after a moment
        time.sleep(0.5)
        if process.poll() is None:
            print(f"{node_id} is running")
            return True
        else:
            print(f"{node_id} failed to start (exit code: {process.poll()})")
            try:
                with open(f"{log_dir}/{node_id}.log", "r") as f:
                    print(f"Log output: {f.read()}")
            except:
                pass
            return False
    except Exception as e:
        print(f"Error starting process: {e}")
        return False

def check_cluster_status():
    """Print the current status of all nodes"""
    node_ids = ["node1", "node2", "node3"]
    
    print("\nCluster Status:")
    print("===============")
    
    for node_id in node_ids:
        pid = find_node_pid(node_id)
        if pid:
            print(f"{node_id}: RUNNING (PID: {pid})")
        else:
            print(f"{node_id}: STOPPED")
    
    print("")
    
    # Try to find the leader
    try:
        result = subprocess.run(["python3", "tools/check_leader.py"], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Leader information:\n{result.stdout}")
        else:
            print(f"Failed to check leader: {result.stderr}")
    except Exception as e:
        print(f"Error checking leader: {e}")

def main():
    parser = argparse.ArgumentParser(description="Manage nodes in the Raft cluster")
    parser.add_argument('action', choices=['kill', 'revive', 'status'], 
                       help='Action to perform')
    parser.add_argument('--node', choices=['node1', 'node2', 'node3'], 
                       help='The ID of the node to manage (required for kill and revive)')
    parser.add_argument('--wait', type=int, default=5,
                       help='Seconds to wait after action before checking status')
    
    args = parser.parse_args()
    
    if args.action in ['kill', 'revive'] and not args.node:
        parser.error(f"The {args.action} action requires --node argument")
    
    # Check status before action
    if args.action != 'status':
        print("Status before action:")
        check_cluster_status()
    
    # Perform the requested action
    if args.action == 'kill':
        kill_node(args.node)
    elif args.action == 'revive':
        revive_node(args.node)
    
    # Wait if requested
    if args.wait > 0 and args.action != 'status':
        print(f"Waiting {args.wait} seconds...")
        time.sleep(args.wait)
    
    # Always show status at the end
    check_cluster_status()

if __name__ == "__main__":
    main()