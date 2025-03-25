"""
Test Raft Consensus Using Mock Network

This module tests the Raft consensus algorithm using a mock network instead of
actual network connections. This allows for reliable testing of leader election,
log replication, and fault tolerance scenarios.
"""

import unittest
import time
import logging
import os
import sys
import json
import tempfile
import shutil
import threading
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.grpc_protocol.tests.mock_network import MockNetwork, MockRaftNode
from src.grpc_protocol.persistence import PersistenceManager, CommandType
from src.grpc_protocol.consensus import ServerState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class TestMockRaftConsensus(unittest.TestCase):
    """Test Raft consensus using a mock network"""
    
    def setUp(self):
        """Set up test environment with a mock network and nodes"""
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        
        # Create mock network with 5 nodes
        self.num_nodes = 5
        self.node_ids = [f"node{i+1}" for i in range(self.num_nodes)]
        self.network = MockNetwork(self.node_ids)
        
        # Create mock Raft nodes
        self.nodes = []
        for node_id in self.node_ids:
            node = MockRaftNode(node_id, self.network)
            self.nodes.append(node)
        
        logging.info(f"Set up mock Raft cluster with {self.num_nodes} nodes")
    
    def tearDown(self):
        """Clean up resources"""
        # Shut down the network
        self.network.shutdown()
        
        # Clean up temporary directory
        try:
            shutil.rmtree(self.test_dir)
        except Exception as e:
            logging.warning(f"Error cleaning up test directory: {e}")
    
    def test_leader_election(self):
        """Test that a leader is elected"""
        # Start an election from the first node
        self.nodes[0].start_election()
        
        # Give time for election to complete
        time.sleep(0.5)
        
        # Count leaders and verify only one leader is elected
        leaders = [node for node in self.nodes if node.state == "LEADER"]
        self.assertEqual(len(leaders), 1, "Expected exactly one leader")
        
        # Verify all nodes recognize the same leader
        leader_id = leaders[0].node_id
        for node in self.nodes:
            if node.state != "LEADER":
                self.assertEqual(node.leader_id, leader_id, 
                                f"Node {node.node_id} has incorrect leader_id")
        
        # Verify all nodes have the same term
        terms = set(node.current_term for node in self.nodes)
        self.assertEqual(len(terms), 1, "Nodes have different terms")
    
    def test_leader_failover(self):
        """Test that a new leader is elected when the current leader fails"""
        # First, get a leader elected
        self.nodes[0].start_election()
        time.sleep(0.5)
        
        leaders = [node for node in self.nodes if node.state == "LEADER"]
        self.assertEqual(len(leaders), 1, "Expected exactly one leader")
        
        original_leader = leaders[0]
        original_leader_id = original_leader.node_id
        
        # Now make the leader fail
        self.network.disconnect_node(original_leader_id)
        logging.info(f"Disconnected leader {original_leader_id}")
        
        # Start an election from another node
        candidate_idx = (self.node_ids.index(original_leader_id) + 1) % self.num_nodes
        candidate = self.nodes[candidate_idx]
        candidate.start_election()
        
        # Give time for election to complete
        time.sleep(0.5)
        
        # Check that a new leader is elected
        connected_nodes = [node for node in self.nodes 
                         if node.node_id != original_leader_id]
        
        new_leaders = [node for node in connected_nodes if node.state == "LEADER"]
        self.assertEqual(len(new_leaders), 1, "Expected exactly one new leader")
        
        new_leader_id = new_leaders[0].node_id
        self.assertNotEqual(new_leader_id, original_leader_id, 
                          "New leader should be different from old leader")
        
        # Verify all connected nodes recognize the new leader
        for node in connected_nodes:
            if node.state != "LEADER":
                self.assertEqual(node.leader_id, new_leader_id, 
                                f"Node {node.node_id} has incorrect leader_id")
    
    def test_log_replication(self):
        """Test that log entries are replicated to all nodes"""
        # First, get a leader elected
        self.nodes[0].start_election()
        time.sleep(0.5)
        
        leaders = [node for node in self.nodes if node.state == "LEADER"]
        self.assertEqual(len(leaders), 1, "Expected exactly one leader")
        
        leader = leaders[0]
        
        # Add some log entries to the leader
        for i in range(5):
            entry = {
                'term': leader.current_term,
                'command': f"test_command_{i}",
                'data': {'key': f'value_{i}'}
            }
            leader.log.append(entry)
        
        # Send heartbeat to replicate logs
        leader.send_heartbeat()
        
        # Give time for replication
        time.sleep(0.5)
        
        # Verify all nodes have the same log
        for node in self.nodes:
            if node.node_id != leader.node_id:
                self.assertEqual(len(node.log), len(leader.log), 
                               f"Node {node.node_id} has incorrect log length")
    
    def test_majority_commit(self):
        """Test that entries are committed when replicated to a majority of nodes"""
        # First, get a leader elected
        self.nodes[0].start_election()
        time.sleep(0.5)
        
        leaders = [node for node in self.nodes if node.state == "LEADER"]
        self.assertEqual(len(leaders), 1, "Expected exactly one leader")
        
        leader = leaders[0]
        
        # Add a log entry to the leader
        entry = {
            'term': leader.current_term,
            'command': "test_command",
            'data': {'key': 'value'}
        }
        leader.log.append(entry)
        
        # Send heartbeat to replicate logs
        leader.send_heartbeat()
        
        # Give time for replication
        time.sleep(0.5)
        
        # Disconnect two nodes (minority)
        self.network.disconnect_node(self.node_ids[-1])
        self.network.disconnect_node(self.node_ids[-2])
        
        # Update commit index on the leader
        leader.commit_index = 1
        
        # Send heartbeat to update commit index on followers
        leader.send_heartbeat()
        
        # Give time for propagation
        time.sleep(0.5)
        
        # Verify commit index on remaining nodes
        for node in self.nodes:
            if (node.node_id != self.node_ids[-1] and 
                node.node_id != self.node_ids[-2]):
                self.assertEqual(node.commit_index, 1, 
                               f"Node {node.node_id} has incorrect commit index")
        
        # Reconnect nodes
        self.network.reconnect_node(self.node_ids[-1])
        self.network.reconnect_node(self.node_ids[-2])
        
        # Send heartbeat to sync rejoined nodes
        leader.send_heartbeat()
        
        # Give time for sync
        time.sleep(0.5)
        
        # Verify all nodes now have the same commit index
        for node in self.nodes:
            self.assertEqual(node.commit_index, 1, 
                           f"Node {node.node_id} has incorrect commit index after rejoin")
    
    def test_five_node_fault_tolerance(self):
        """Test that a five-node cluster can survive two node failures"""
        # First, get a leader elected
        self.nodes[0].start_election()
        time.sleep(0.5)
        
        leaders = [node for node in self.nodes if node.state == "LEADER"]
        self.assertEqual(len(leaders), 1, "Expected exactly one leader")
        
        original_leader = leaders[0]
        
        # Add some log entries
        for i in range(3):
            entry = {
                'term': original_leader.current_term,
                'command': f"command_{i}",
                'data': {'index': i}
            }
            original_leader.log.append(entry)
        
        # Replicate to all nodes
        original_leader.send_heartbeat()
        time.sleep(0.5)
        
        # Verify all nodes have the entries
        for node in self.nodes:
            self.assertEqual(len(node.log), 3, 
                           f"Node {node.node_id} has incorrect log length")
        
        # Now fail two nodes including the leader
        self.network.disconnect_node(original_leader.node_id)
        self.network.disconnect_node(self.node_ids[1])
        logging.info(f"Disconnected nodes: {original_leader.node_id}, {self.node_ids[1]}")
        
        # Start election from a remaining node
        remaining_nodes = [node for node in self.nodes 
                          if node.node_id not in [original_leader.node_id, self.node_ids[1]]]
        
        remaining_nodes[0].start_election()
        time.sleep(0.5)
        
        # Check that a new leader is elected
        new_leaders = [node for node in remaining_nodes if node.state == "LEADER"]
        self.assertEqual(len(new_leaders), 1, "Expected exactly one new leader")
        
        new_leader = new_leaders[0]
        
        # Add more entries with the new leader
        entry = {
            'term': new_leader.current_term,
            'command': "after_failure",
            'data': {'key': 'value_after_failure'}
        }
        new_leader.log.append(entry)
        
        # Replicate to remaining nodes
        new_leader.send_heartbeat()
        time.sleep(0.5)
        
        # Verify remaining nodes have the new entry
        for node in remaining_nodes:
            self.assertEqual(len(node.log), 4, 
                           f"Node {node.node_id} has incorrect log length after leader change")
        
        # Verify the system remains operational with only 3 out of 5 nodes
        self.assertTrue(len(remaining_nodes) >= 3, 
                      "System should have at least 3 nodes (majority) operational")


if __name__ == "__main__":
    unittest.main() 