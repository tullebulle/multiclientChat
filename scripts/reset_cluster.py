#!/usr/bin/env python3
"""
Reset the cluster by clearing all databases and restarting servers. REMOVING ALL DATA AND LOGS AND STARTS AGAIN.
"""

import os
import sys
import time
import shutil
import subprocess

def reset_cluster():
    """Reset the Raft cluster by clearing all data and restarting servers"""
    print("===== RESET CLUSTER SCRIPT STARTING =====")
    print("Current working directory:", os.getcwd())
    print("Resetting the Raft cluster...")
    
    # Step 1: Stop all servers
    print("Stopping all servers...")
    try:
        print("Running: python3 scripts/start_cluster_mp.py stop")
        subprocess.run(["python3", "scripts/start_cluster_mp.py", "stop"], check=True)
        print("Server stop command completed successfully")
        time.sleep(2)  # Give some time for processes to terminate
    except subprocess.CalledProcessError as e:
        print(f"Error stopping servers: {e}")
        print("Attempting to continue...")
    
    # Step 2: Remove all database files and logs
    print("Removing database files and logs...")
    try:
        # Reset data directory
        if os.path.exists("./data"):
            print("Removing data directory")
            shutil.rmtree("./data")
            os.makedirs("./data", exist_ok=True)
            print("Data directory recreated")
            
        # Reset logs directories
        if os.path.exists("./logs"):
            print("Removing logs directory")
            shutil.rmtree("./logs")
        os.makedirs("./logs", exist_ok=True)
        os.makedirs("./logs/diagnosis", exist_ok=True)
        print("Log directories recreated")
    except Exception as e:
        print(f"Error setting up directories: {e}")
        return
    
    # Step 3: Restart the servers using multiprocessing
    print("Starting servers with clean databases...")
    try:
        # Start the subprocess but don't wait for it to complete
        print("Running: python3 scripts/start_cluster_mp.py start")
        cluster_process = subprocess.Popen(["python3", "scripts/start_cluster_mp.py", "start"])
        print(f"Started cluster process with PID: {cluster_process.pid}")
    except Exception as e:
        print(f"Error starting servers: {e}")
        return
    
    print("Waiting for leader election...")
    time.sleep(7)  # Give more time for leader election
    
    # Check if server processes are still running
    print("Checking if server processes are still running...")
    try:
        ps_output = subprocess.check_output(["ps", "-ef"]).decode()
        server_count = 0
        for line in ps_output.split('\n'):
            if "run_server.py" in line and "python" in line:
                print(f"Found server process: {line}")
                server_count += 1
        print(f"Found {server_count} running server processes")
    except Exception as e:
        print(f"Error checking processes: {e}")
    
    # Step 4: Check the cluster
    print("Checking cluster state...")
    try:
        print("Running: python3 tools/check_leader.py")
        result = subprocess.run(["python3", "tools/check_leader.py"], check=True, capture_output=True, text=True)
        print(f"Check leader output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Error checking leader: {e}")
        print(f"Error output: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
    
    print("\n===== CLUSTER RESET COMPLETED =====")
    print("The cluster should now be in a clean state.")
    print("The cluster is running in the background. To stop it later, run:")
    print("  python3 scripts/start_cluster_mp.py stop")

if __name__ == "__main__":
    reset_cluster() 