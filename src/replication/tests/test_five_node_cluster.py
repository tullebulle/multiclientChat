"""
Test Five-Node Raft Cluster

This module tests a five-node Raft cluster to verify it can survive up to two node failures,
meeting our fault tolerance requirements. This is a more extensive test than the basic
multi-node test and simulates real-world failure scenarios.
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

from src.replication.consensus import RaftNode, NotLeaderError, ServerState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class TestFiveNodeCluster(unittest.TestCase):
    """Test case for a five-node Raft cluster with fault tolerance"""
    
    def setUp(self):
        """Set up test database and Raft nodes before each test"""
        # Create a temporary directory for all node data
        self.test_dir = tempfile.mkdtemp()
        
        # Set up five nodes
        self.num_nodes = 5
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
            try:
                node.shutdown()
            except:
                pass
        
        # Remove the temporary directory
        try:
            shutil.rmtree(self.test_dir)
        except Exception as e:
            logging.warning(f"Error deleting temporary directory: {e}")
    
    def test_two_node_failure(self):
        """Test that the cluster can survive two node failures"""
        # Find the leader
        leader = None
        for node in self.nodes:
            if node.state == ServerState.LEADER:
                leader = node
                break
        
        self.assertIsNotNone(leader, "No leader found")
        logging.info(f"Initial leader is {leader.node_id}")
        
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
        
        # Now fail two nodes
        # If the leader is one of them, this will also test leader election
        nodes_to_fail = random.sample(self.nodes, 2)
        failed_nodes_ids = [node.node_id for node in nodes_to_fail]
        logging.info(f"Failing nodes: {failed_nodes_ids}")
        
        for node in nodes_to_fail:
            node.shutdown()
            self.nodes.remove(node)
        
        # Give time for recovery and possible leader election
        time.sleep(5.0)
        
        # Find new leader
        new_leader = None
        for node in self.nodes:
            if node.state == ServerState.LEADER:
                new_leader = node
                break
        
        self.assertIsNotNone(new_leader, "No leader found after node failures")
        logging.info(f"New leader after failures: {new_leader.node_id}")
        
        # Try operations after failures
        # Create a third account
        success = new_leader.create_account(
            username="charlie",
            password_hash="hash3"
        )
        
        self.assertTrue(success)
        
        # Give time for replication
        time.sleep(2.0)
        
        # Verify all remaining nodes have the new data
        for node in self.nodes:
            # Check users
            users = node.persistence.list_users()
            self.assertIn("alice", users)
            self.assertIn("bob", users)
            self.assertIn("charlie", users)

if __name__ == "__main__":
    unittest.main() 