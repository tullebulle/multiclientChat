#!/usr/bin/env python3
"""
Simple script to check the status of each node in the cluster
"""
import sys
import time
import logging
import grpc

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add parent directory to Python path
sys.path.append(".")
from src.grpc_protocol import chat_pb2, chat_pb2_grpc

def check_node(address):
    """Check the status of a specific node"""
    print(f"\nChecking {address}...")
    try:
        # Create a channel with a shorter timeout
        channel = grpc.insecure_channel(address)
        # Create a shorter deadline
        stub = chat_pb2_grpc.ChatServiceStub(channel)
        
        try:
            # Try to get the cluster status
            request = chat_pb2.ClusterStatusRequest()
            # Use a much shorter timeout
            response = stub.GetClusterStatus(request, timeout=2.0)
            
            print(f"Node {response.node_id}:")
            print(f"  State: {response.state}")
            print(f"  Leader: {response.leader_id or 'None'}")
            print(f"  Current term: {response.current_term}")
            print(f"  Commit index: {response.commit_index}")
            print(f"  Last applied: {response.last_applied}")
            
            # Try to list accounts
            try:
                accounts_request = chat_pb2.ListAccountsRequest(pattern="*")
                accounts_response = stub.ListAccounts(accounts_request, timeout=2.0)
                print(f"  Users: {list(accounts_response.usernames)}")
            except Exception as e:
                print(f"  Error listing accounts: {e}")
            
            # Was this successful?
            return True
            
        except grpc.RpcError as e:
            print(f"  Error: {e.code()}: {e.details()}")
        except Exception as e:
            print(f"  Error: {e}")
        finally:
            channel.close()
            
    except Exception as e:
        print(f"  Connection error: {e}")
    
    return False

def main():
    """Check all nodes in the cluster"""
    print("Checking nodes in the cluster...\n")
    
    # Check each node
    success = False
    for port in [9001, 9002, 9003]:
        address = f"localhost:{port}"
        success = check_node(address) or success
    
    if not success:
        print("\nWarning: Could not connect to any nodes. Is the cluster running?")
        print("Try starting the cluster: ./start_cluster.sh start")
    
if __name__ == "__main__":
    main() 