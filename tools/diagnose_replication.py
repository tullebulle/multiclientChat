#!/usr/bin/env python3
"""
Diagnostic script to trace a single operation through the Raft consensus process
and verify its replication across all nodes.
"""

import os
import sys
import time
import uuid
import logging
import argparse
from typing import List, Dict, Any

# Add the parent directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.grpc_protocol.client import GRPCChatClient
import src.grpc_protocol.chat_pb2 as chat_pb2

# Configure detailed logging
log_filename = f"logs/diagnosis/diagnose_replication_{int(time.time())}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("replication_diagnosis")

# Define server addresses
SERVERS = [
    "localhost:9001",  # node1 
    "localhost:9002",  # node2
    "localhost:9003",  # node3
]

def check_leader() -> str:
    """
    Find which node is currently the leader.
    
    Returns:
        str: The address of the leader node, or None if no leader found.
    """
    logger.info("=== CHECKING LEADER ===")
    for address in SERVERS:
        try:
            client = GRPCChatClient(address)
            status = client.get_status()
            client.close()
            
            logger.info(f"Status from {address}: {status}")
            
            if status.get('state') == 'LEADER':
                logger.info(f"Found leader at {address}")
                return address
        except Exception as e:
            logger.error(f"Error connecting to {address}: {e}")
    
    logger.warning("No leader found in the cluster!")
    return None

def check_node_state(address: str) -> Dict[str, Any]:
    """
    Check the state of a specific node.
    
    Args:
        address: Server address to check
        
    Returns:
        Dict with node state information
    """
    try:
        client = GRPCChatClient(address)
        status = client.get_status()
        users = client.list_accounts()[0]  # Just get the users list
        client.close()
        
        state = {
            "address": address,
            "state": status.get('state', 'UNKNOWN'),
            "term": status.get('term', 0),
            "leader": status.get('leader_id', 'UNKNOWN'),
            "commit_index": status.get('commit_index', 0),
            "last_applied": status.get('last_applied', 0),
            "users": users
        }
        
        logger.info(f"State of {address}: {state}")
        return state
    except Exception as e:
        logger.error(f"Error checking state of {address}: {e}")
        return {
            "address": address,
            "error": str(e)
        }

def check_all_nodes() -> List[Dict[str, Any]]:
    """
    Check the state of all nodes in the cluster.
    
    Returns:
        List of node states
    """
    logger.info("=== CHECKING ALL NODES ===")
    return [check_node_state(address) for address in SERVERS]

def perform_operation(leader_address: str, operation_type: str) -> bool:
    """
    Perform a single operation on the leader and trace its progress.
    
    Args:
        leader_address: The address of the leader node
        operation_type: Type of operation to perform ("create_user" or "send_message")
        
    Returns:
        bool: Whether the operation was successful
    """
    logger.info(f"=== PERFORMING OPERATION: {operation_type} ===")
    
    try:
        client = GRPCChatClient(leader_address)
        
        # Generate a unique identifier for this test
        test_id = f"{int(time.time())}"
        
        if operation_type == "create_user":
            username = f"user_test_{test_id}"
            password = "testpass123"
            
            logger.info(f"Creating user: {username}")
            success, error = client.create_account(username, password)
            
            if success:
                logger.info(f"Successfully created user {username}")
            else:
                logger.error(f"Failed to create user: {error}")
                
            client.close()
            return success
            
        elif operation_type == "send_message":
            # First ensure we have two users
            alice = f"alice_test_{test_id}"
            bob = f"bob_test_{test_id}"
            
            logger.info(f"Creating users for message test: {alice} and {bob}")
            client.create_account(alice, "testpass123")
            client.create_account(bob, "testpass123")
            
            # Send a message
            message = f"Test message at {time.time()}"
            logger.info(f"Sending message from {alice} to {bob}: '{message}'")
            
            # Authenticate as alice
            success, _ = client.login(alice, "testpass123")
            if not success:
                logger.error(f"Failed to authenticate as {alice}")
                client.close()
                return False
                
            # Send the message
            msg_id, error = client.send_message(bob, message)
            
            if msg_id > 0:
                logger.info(f"Successfully sent message with ID: {msg_id}")
                client.close()
                return True
            else:
                logger.error(f"Failed to send message: {error}")
                client.close()
                return False
        else:
            logger.error(f"Unknown operation type: {operation_type}")
            client.close()
            return False
            
    except Exception as e:
        logger.error(f"Error performing operation: {e}")
        return False

def verify_replication(operation_type: str, test_id: str) -> bool:
    """
    Verify that the operation was replicated to all nodes.
    
    Args:
        operation_type: Type of operation that was performed
        test_id: Unique identifier for the test
        
    Returns:
        bool: Whether replication was successful across all nodes
    """
    logger.info(f"=== VERIFYING REPLICATION ===")
    
    # Wait for replication to complete
    logger.info("Waiting for replication to complete...")
    time.sleep(5)
    
    # Check all nodes
    node_states = check_all_nodes()
    
    # Verify based on operation type
    if operation_type == "create_user":
        username = f"user_test_{test_id}"
        
        # Check if the user exists on all nodes
        for state in node_states:
            if 'users' in state and username in state['users']:
                logger.info(f"User {username} found on {state['address']} ✓")
            else:
                logger.warning(f"User {username} NOT found on {state['address']} ✗")
                return False
        
        return True
        
    elif operation_type == "send_message":
        # This is more complex as we'd need to check message tables
        # For now, just verify that both users exist on all nodes
        alice = f"alice_test_{test_id}"
        bob = f"bob_test_{test_id}"
        
        all_consistent = True
        
        for state in node_states:
            if 'users' in state and alice in state['users'] and bob in state['users']:
                logger.info(f"Users {alice} and {bob} found on {state['address']} ✓")
            else:
                logger.warning(f"Users {alice} and {bob} NOT found on {state['address']} ✗")
                all_consistent = False
        
        return all_consistent
    
    return False

def diagnose_single_operation(operation_type: str) -> None:
    """
    Perform a complete diagnostic test of a single operation.
    
    Args:
        operation_type: Type of operation to test
    """
    logger.info("=== STARTING REPLICATION DIAGNOSIS ===")
    logger.info(f"Testing operation: {operation_type}")
    
    # Step 1: Check initial state of all nodes
    logger.info("Checking initial state of all nodes...")
    initial_states = check_all_nodes()
    
    # Step 2: Find the leader
    leader_address = check_leader()
    if not leader_address:
        logger.error("Cannot continue without a leader!")
        return
    
    # Step 3: Perform the operation
    test_id = f"{int(time.time())}"
    success = perform_operation(leader_address, operation_type)
    if not success:
        logger.error("Operation failed, cannot verify replication!")
        return
    
    # Step 4: Verify replication
    replication_success = verify_replication(operation_type, test_id)
    
    # Step 5: Final state check
    logger.info("Checking final state of all nodes...")
    final_states = check_all_nodes()
    
    # Step 6: Summary
    logger.info("=== DIAGNOSIS SUMMARY ===")
    if replication_success:
        logger.info("REPLICATION SUCCESS: Operation was successfully replicated to all nodes!")
    else:
        logger.error("REPLICATION FAILURE: Operation was not properly replicated!")
    
    # Compare initial and final states
    logger.info("State changes:")
    for i, state in enumerate(initial_states):
        addr = state.get('address')
        initial_commit = state.get('commit_index', 0)
        initial_applied = state.get('last_applied', 0)
        final_commit = final_states[i].get('commit_index', 0)
        final_applied = final_states[i].get('last_applied', 0)
        
        logger.info(f"{addr}: commit_index {initial_commit} -> {final_commit}, "
                   f"last_applied {initial_applied} -> {final_applied}")
    
    logger.info("=== DIAGNOSIS COMPLETE ===")

def main():
    parser = argparse.ArgumentParser(description="Diagnose Raft replication issues")
    parser.add_argument('--operation', choices=['create_user', 'send_message'], 
                       default='create_user', help='Operation to test')
    
    args = parser.parse_args()
    
    diagnose_single_operation(args.operation)

if __name__ == "__main__":
    main() 