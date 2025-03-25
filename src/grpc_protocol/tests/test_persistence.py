"""
Tests for PersistenceManager

This module contains unit tests for the PersistenceManager class.
"""

import unittest
import os
import sys
import tempfile
import logging
import time

# Add the parent directory to sys.path to allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.replication.persistence import PersistenceManager, CommandType

# Configure logging
logging.basicConfig(level=logging.INFO)

class TestPersistenceManager(unittest.TestCase):
    """Test cases for PersistenceManager class"""
    
    def setUp(self):
        """Set up a test database before each test"""
        # Create a temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        
        # Initialize the persistence manager
        self.persistence = PersistenceManager(self.temp_db.name)
    
    def tearDown(self):
        """Clean up after each test"""
        # Close database connection
        self.persistence.conn.close()
        
        # Delete the temporary database file
        try:
            os.unlink(self.temp_db.name)
        except Exception as e:
            logging.warning(f"Error deleting temporary database: {e}")
    
    def test_user_management(self):
        """Test user management operations"""
        # Test creating users
        self.assertTrue(self.persistence.create_user("alice", "hash1"))
        self.assertTrue(self.persistence.create_user("bob", "hash2"))
        
        # Test duplicate username
        self.assertFalse(self.persistence.create_user("alice", "hash3"))
        
        # Test authentication
        self.assertTrue(self.persistence.authenticate_user("alice", "hash1"))
        self.assertFalse(self.persistence.authenticate_user("alice", "wrong_hash"))
        self.assertFalse(self.persistence.authenticate_user("nonexistent", "hash"))
        
        # Test listing users
        users = self.persistence.list_users()
        self.assertEqual(len(users), 2)
        self.assertIn("alice", users)
        self.assertIn("bob", users)
        
        # Test listing users with pattern
        users = self.persistence.list_users("a")
        self.assertEqual(len(users), 1)
        self.assertIn("alice", users)
        
        # Test deleting users
        self.assertTrue(self.persistence.delete_user("bob"))
        users = self.persistence.list_users()
        self.assertEqual(len(users), 1)
        self.assertIn("alice", users)
        
        # Test deleting nonexistent user
        self.assertFalse(self.persistence.delete_user("nonexistent"))
    
    def test_message_management(self):
        """Test message management operations"""
        # Create test users
        self.persistence.create_user("alice", "hash1")
        self.persistence.create_user("bob", "hash2")
        
        # Test adding messages
        msg1_id = self.persistence.add_message("alice", "bob", "Hello Bob!")
        self.assertGreater(msg1_id, 0)
        
        msg2_id = self.persistence.add_message("bob", "alice", "Hello Alice!")
        self.assertGreater(msg2_id, 0)
        
        # Test getting messages
        alice_messages = self.persistence.get_messages("alice")
        self.assertEqual(len(alice_messages), 1)
        self.assertEqual(alice_messages[0]["sender"], "bob")
        self.assertEqual(alice_messages[0]["content"], "Hello Alice!")
        
        bob_messages = self.persistence.get_messages("bob")
        self.assertEqual(len(bob_messages), 1)
        self.assertEqual(bob_messages[0]["sender"], "alice")
        self.assertEqual(bob_messages[0]["content"], "Hello Bob!")
        
        # Test marking messages as read
        self.assertTrue(self.persistence.mark_read("alice", [alice_messages[0]["id"]]))
        
        # Test getting unread messages
        alice_unread = self.persistence.get_messages("alice")
        self.assertEqual(len(alice_unread), 0)
        
        # Test including read messages
        alice_all = self.persistence.get_messages("alice", include_read=True)
        self.assertEqual(len(alice_all), 1)
        
        # Test unread count
        self.assertEqual(self.persistence.get_unread_count("alice"), 0)
        self.assertEqual(self.persistence.get_unread_count("bob"), 1)
        
        # Test deleting messages
        self.assertTrue(self.persistence.delete_messages("bob", [bob_messages[0]["id"]]))
        bob_after_delete = self.persistence.get_messages("bob", include_read=True)
        self.assertEqual(len(bob_after_delete), 0)
    
    def test_raft_log(self):
        """Test Raft log operations"""
        # Test appending log entries
        entry1 = self.persistence.append_log_entry(
            term=1,
            command_type=CommandType.CREATE_ACCOUNT,
            data={"username": "alice", "password_hash": "hash1"}
        )
        self.assertGreater(entry1, 0)
        
        entry2 = self.persistence.append_log_entry(
            term=1,
            command_type=CommandType.SEND_MESSAGE,
            data={"sender": "alice", "recipient": "bob", "content": "Hello"}
        )
        self.assertGreater(entry2, 0)
        self.assertEqual(entry2, entry1 + 1)
        
        # Test getting log entries
        log_entry = self.persistence.get_log_entry(entry1)
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry["term"], 1)
        self.assertEqual(log_entry["command_type"], CommandType.CREATE_ACCOUNT)
        self.assertEqual(log_entry["data"]["username"], "alice")
        
        # Test getting range of log entries
        entries = self.persistence.get_log_entries(1)
        self.assertEqual(len(entries), 2)
        
        # Test getting last log index and term
        last_index, last_term = self.persistence.get_last_log_index_and_term()
        self.assertEqual(last_index, entry2)
        self.assertEqual(last_term, 1)
        
        # Test deleting logs
        self.assertTrue(self.persistence.delete_logs_from(entry2))
        entries_after_delete = self.persistence.get_log_entries(1)
        self.assertEqual(len(entries_after_delete), 1)
        
        # Test clearing all logs
        self.assertTrue(self.persistence.delete_logs_from(1))
        all_entries = self.persistence.get_log_entries(1)
        self.assertEqual(len(all_entries), 0)
        
        # Test last index and term with empty log
        empty_index, empty_term = self.persistence.get_last_log_index_and_term()
        self.assertEqual(empty_index, 0)
        self.assertEqual(empty_term, 0)
    
    def test_metadata(self):
        """Test metadata operations"""
        # Test saving and retrieving strings
        self.assertTrue(self.persistence.save_metadata("key1", "value1"))
        self.assertEqual(self.persistence.get_metadata("key1"), "value1")
        
        # Test saving and retrieving numbers
        self.assertTrue(self.persistence.save_metadata("key2", 42))
        self.assertEqual(self.persistence.get_metadata("key2"), 42)
        
        # Test saving and retrieving dictionaries
        data = {"name": "alice", "age": 30}
        self.assertTrue(self.persistence.save_metadata("key3", data))
        retrieved = self.persistence.get_metadata("key3")
        self.assertEqual(retrieved, data)
        
        # Test default value for nonexistent keys
        self.assertIsNone(self.persistence.get_metadata("nonexistent"))
        self.assertEqual(self.persistence.get_metadata("nonexistent", "default"), "default")
        
        # Test Raft-specific metadata
        self.assertTrue(self.persistence.set_current_term(3))
        self.assertEqual(self.persistence.get_current_term(), 3)
        
        self.assertTrue(self.persistence.set_voted_for("node2"))
        self.assertEqual(self.persistence.get_voted_for(), "node2")
        
        self.assertTrue(self.persistence.set_voted_for(None))
        self.assertIsNone(self.persistence.get_voted_for())

if __name__ == "__main__":
    unittest.main() 