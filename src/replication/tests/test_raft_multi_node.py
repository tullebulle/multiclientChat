"""
Test Raft Consensus - Multiple Nodes

This module tests the functionality of the Raft consensus algorithm
with multiple nodes. It verifies that leader election, log replication,
and consensus work correctly across multiple nodes.
"""

import os
import sys
import time
import logging
import tempfile
import unittest
import threading
import shutil
import random

# Add parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.grpc_protocol.consensus import RaftNode, NotLeaderError, ServerState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class TestRaftMultiNode(unittest.TestCase):
    """Test case for a multi-node Raft setup"""
    
    def setUp(self):
        """Set up test database and Raft nodes before each test"""
        # Create a temporary directory for all node data
        self.test_dir = tempfile.mkdtemp()
        
        # Set up three nodes
        self.num_nodes = 3
        self.nodes = []
        self.node_ids = [f"node{i+1}" for i in range(self.num_nodes)]
        
        # Create peer address maps for each node
        # Each node connects to all other nodes
        peer_addresses = {}
        
        # Use port numbers starting at 50051
        base_port = 50051
        for i, node_id in enumerate(self.node_ids):
            port = base_port + i
            # For each node, map node_id -> localhost:port
            peer_addresses[node_id] = f"localhost:{port}"
        
        # Create nodes
        for i, node_id in enumerate(self.node_ids):
            db_path = os.path.join(self.test_dir, f"{node_id}.db")
            
            # Create a copy of peer_addresses without this node
            this_node_peers = {nid: addr for nid, addr in peer_addresses.items() if nid != node_id}
            
            # Create the node
            node = RaftNode(
                node_id=node_id,
                db_path=db_path,
                peer_addresses=this_node_peers
            )
            
            self.nodes.append(node)
        
        # Give the nodes time to initialize and elect a leader
        time.sleep(3.0)
    
    def tearDown(self):
        """Clean up after each test"""
        # Shut down all Raft nodes
        for node in self.nodes:
            node.shutdown()
        
        # Remove the temporary directory
        try:
            shutil.rmtree(self.test_dir)
        except Exception as e:
            logging.warning(f"Error deleting temporary directory: {e}")
    
    def test_leader_election(self):
        """Test that exactly one leader is elected"""
        # Give the nodes time to elect a leader
        time.sleep(5.0)
        
        # Count leaders
        leaders = [node for node in self.nodes if node.state == ServerState.LEADER]
        
        # There should be exactly one leader
        self.assertEqual(len(leaders), 1)
        
        # All nodes should have the same leader_id
        leader_id = leaders[0].node_id
        for node in self.nodes:
            self.assertEqual(node.leader_id, leader_id)
            
        # All nodes should have the same term
        term = leaders[0].current_term
        for node in self.nodes:
            self.assertEqual(node.current_term, term)
    
    def test_log_replication(self):
        """Test that log entries are replicated to all nodes"""
        # Find the leader
        leader = None
        for node in self.nodes:
            if node.state == ServerState.LEADER:
                leader = node
                break
        
        self.assertIsNotNone(leader, "No leader found")
        
        # Create a test account
        success = leader.create_account(
            username="alice",
            password_hash="hash1"
        )
        
        self.assertTrue(success)
        
        # Give time for replication
        time.sleep(2.0)
        
        # Create another account
        success = leader.create_account(
            username="bob",
            password_hash="hash2"
        )
        
        self.assertTrue(success)
        
        # Give time for replication
        time.sleep(2.0)
        
        # Send a message
        msg_id = leader.send_message(
            sender="alice",
            recipient="bob",
            content="Hello, Bob!"
        )
        
        self.assertGreater(msg_id, 0)
        
        # Give time for replication
        time.sleep(2.0)
        
        # Verify all nodes have the same log state
        last_index, last_term = leader.persistence.get_last_log_index_and_term()
        
        for node in self.nodes:
            index, term = node.persistence.get_last_log_index_and_term()
            self.assertEqual(index, last_index)
            self.assertEqual(term, last_term)
        
        # Verify all nodes have the messages
        for node in self.nodes:
            # Check users
            users = node.persistence.list_users()
            self.assertIn("alice", users)
            self.assertIn("bob", users)
            
            # Check message from alice to bob
            if node.state != ServerState.LEADER:
                # For non-leaders, directly query the persistence layer
                messages = node.persistence.get_messages("bob", include_read=True)
                self.assertEqual(len(messages), 1)
                self.assertEqual(messages[0]["sender"], "alice")
                self.assertEqual(messages[0]["content"], "Hello, Bob!")
    
    def test_leader_failure(self):
        """Test that a new leader is elected when the current leader fails"""
        # Find the current leader
        old_leader = None
        for node in self.nodes:
            if node.state == ServerState.LEADER:
                old_leader = node
                break
        
        self.assertIsNotNone(old_leader, "No leader found")
        old_leader_id = old_leader.node_id
        
        # Shut down the leader
        old_leader.shutdown()
        
        # Remove the leader from our list
        self.nodes.remove(old_leader)
        
        # Give time for a new leader election
        time.sleep(5.0)
        
        # Verify a new leader is elected
        new_leaders = [node for node in self.nodes if node.state == ServerState.LEADER]
        self.assertEqual(len(new_leaders), 1)
        
        new_leader = new_leaders[0]
        self.assertNotEqual(new_leader.node_id, old_leader_id)
        
        # Verify all remaining nodes recognize the new leader
        for node in self.nodes:
            self.assertEqual(node.leader_id, new_leader.node_id)

if __name__ == "__main__":
    unittest.main() 