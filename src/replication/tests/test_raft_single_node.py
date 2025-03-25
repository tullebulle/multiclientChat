"""
Test Raft Consensus - Single Node

This module tests the basic functionality of the Raft consensus algorithm
with a single node. This verifies that the state machine operations work
correctly without the complexity of multiple nodes.
"""

import os
import sys
import time
import logging
import tempfile
import unittest
import threading
import shutil

# Add parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.grpc_protocol.consensus import RaftNode, NotLeaderError, ServerState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class TestRaftSingleNode(unittest.TestCase):
    """Test case for a single-node Raft setup"""
    
    def setUp(self):
        """Set up a test database and Raft node before each test"""
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_raft.db")
        logging.info(f"Using test database at {self.db_path}")
        
        # Create a single-node Raft cluster (no peers)
        self.node_id = "node1"
        self.node = RaftNode(
            node_id=self.node_id,
            db_path=self.db_path,
            peer_addresses={}  # No peers for single-node test
        )
        
        # Give the node time to initialize
        time.sleep(0.5)
    
    def tearDown(self):
        """Clean up after each test"""
        # Shut down the Raft node
        if hasattr(self, 'node'):
            self.node.shutdown()
        
        # Remove the temporary directory
        try:
            shutil.rmtree(self.test_dir)
        except Exception as e:
            logging.warning(f"Error deleting temporary directory: {e}")
    
    def test_become_leader(self):
        """Test that a single node becomes leader automatically"""
        # Since there are no peers, it should become leader after election
        deadline = time.time() + 5.0  # 5-second timeout
        
        while time.time() < deadline:
            if self.node.state == ServerState.LEADER:
                break
            time.sleep(0.1)
        
        self.assertEqual(self.node.state, ServerState.LEADER)
        self.assertEqual(self.node.leader_id, self.node_id)
        self.assertEqual(self.node.current_term, 1)
    
    def test_create_account(self):
        """Test creating an account through Raft consensus"""
        # Wait for node to become leader
        deadline = time.time() + 5.0
        while time.time() < deadline and self.node.state != ServerState.LEADER:
            time.sleep(0.1)
        
        # Create a test account
        success = self.node.create_account(
            username="alice",
            password_hash="hash1"
        )
        
        self.assertTrue(success)
        
        # Verify account was created
        users = self.node.persistence.list_users()
        self.assertIn("alice", users)
    
    def test_send_message(self):
        """Test sending a message through Raft consensus"""
        # Wait for node to become leader
        deadline = time.time() + 5.0
        while time.time() < deadline and self.node.state != ServerState.LEADER:
            time.sleep(0.1)
        
        # Create test accounts
        self.node.create_account("alice", "hash1")
        self.node.create_account("bob", "hash2")
        
        # Send a message
        message_id = self.node.send_message(
            sender="alice",
            recipient="bob",
            content="Hello, Bob!"
        )
        
        self.assertGreater(message_id, 0)
        
        # Verify message was sent
        messages = self.node.persistence.get_messages("bob")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["sender"], "alice")
        self.assertEqual(messages[0]["content"], "Hello, Bob!")
    
    def test_mark_messages_read(self):
        """Test marking messages as read through Raft consensus"""
        # Wait for node to become leader
        deadline = time.time() + 5.0
        while time.time() < deadline and self.node.state != ServerState.LEADER:
            time.sleep(0.1)
        
        # Create test accounts
        self.node.create_account("alice", "hash1")
        self.node.create_account("bob", "hash2")
        
        # Send a message
        message_id = self.node.persistence.add_message(
            sender="alice",
            recipient="bob",
            content="Hello, Bob!"
        )
        
        # Verify message is unread
        messages = self.node.persistence.get_messages("bob")
        self.assertEqual(len(messages), 1)
        self.assertFalse(messages[0]["is_read"])
        
        # Mark message as read
        success = self.node.mark_messages_read(
            username="bob",
            message_ids=[message_id]
        )
        
        self.assertTrue(success)
        
        # Verify message is now read
        unread_messages = self.node.persistence.get_messages("bob")
        self.assertEqual(len(unread_messages), 0)
        
        all_messages = self.node.persistence.get_messages("bob", include_read=True)
        self.assertEqual(len(all_messages), 1)
        self.assertTrue(all_messages[0]["is_read"])
    
    def test_delete_messages(self):
        """Test deleting messages through Raft consensus"""
        # Wait for node to become leader
        deadline = time.time() + 5.0
        while time.time() < deadline and self.node.state != ServerState.LEADER:
            time.sleep(0.1)
        
        # Create test accounts
        self.node.create_account("alice", "hash1")
        self.node.create_account("bob", "hash2")
        
        # Send a message
        message_id = self.node.persistence.add_message(
            sender="alice",
            recipient="bob",
            content="Hello, Bob!"
        )
        
        # Verify message exists
        messages = self.node.persistence.get_messages("bob", include_read=True)
        self.assertEqual(len(messages), 1)
        
        # Delete message
        success = self.node.delete_messages(
            username="bob",
            message_ids=[message_id]
        )
        
        self.assertTrue(success)
        
        # Verify message is deleted
        messages = self.node.persistence.get_messages("bob", include_read=True)
        self.assertEqual(len(messages), 0)
    
    def test_delete_account(self):
        """Test deleting an account through Raft consensus"""
        # Wait for node to become leader
        deadline = time.time() + 5.0
        while time.time() < deadline and self.node.state != ServerState.LEADER:
            time.sleep(0.1)
        
        # Create a test account
        self.node.create_account("alice", "hash1")
        
        # Verify account exists
        users = self.node.persistence.list_users()
        self.assertIn("alice", users)
        
        # Delete account
        success = self.node.delete_account("alice")
        
        self.assertTrue(success)
        
        # Verify account is deleted
        users = self.node.persistence.list_users()
        self.assertNotIn("alice", users)
    
    def test_log_persistence(self):
        """Test that log entries are persisted"""
        # Wait for node to become leader
        deadline = time.time() + 5.0
        while time.time() < deadline and self.node.state != ServerState.LEADER:
            time.sleep(0.1)
        
        # Create a test account
        self.node.create_account("alice", "hash1")
        
        # Verify log entry was created
        last_index, last_term = self.node.persistence.get_last_log_index_and_term()
        self.assertEqual(last_index, 1)
        self.assertEqual(last_term, 1)
        
        # Send a message
        self.node.create_account("bob", "hash2")
        self.node.send_message("alice", "bob", "Hello, Bob!")
        
        # Verify log entries were created
        last_index, last_term = self.node.persistence.get_last_log_index_and_term()
        self.assertEqual(last_index, 3)
        self.assertEqual(last_term, 1)

if __name__ == "__main__":
    unittest.main() 