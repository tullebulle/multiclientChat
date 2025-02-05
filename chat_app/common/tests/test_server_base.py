"""
Tests for common server functionality
"""

import unittest
from datetime import datetime, timedelta
from ..server_base import ChatServer, Message

class TestChatServer(unittest.TestCase):
    """Test cases for ChatServer class"""
    
    def setUp(self):
        """Set up a fresh server and create test users for each test"""
        self.server = ChatServer()
        
        # Create test users
        self.server.create_account("alice", "pass1")
        self.server.create_account("bob", "pass2")
        self.server.create_account("charlie", "pass3")
    
    def test_send_message(self):
        """Test sending messages between users"""
        # Send a message
        msg = self.server.send_message("alice", "bob", "Hello Bob!")
        
        # Verify message properties
        self.assertEqual(msg.sender, "alice")
        self.assertEqual(msg.recipient, "bob")
        self.assertEqual(msg.content, "Hello Bob!")
        self.assertFalse(msg.is_read)
        self.assertIsInstance(msg.timestamp, datetime)
        
        # Verify unread count
        self.assertEqual(self.server.get_unread_count("bob"), 1)
        
        # Test invalid users
        with self.assertRaises(ValueError):
            self.server.send_message("nonexistent", "bob", "Hello")
        with self.assertRaises(ValueError):
            self.server.send_message("alice", "nonexistent", "Hello")
    
    def test_get_messages(self):
        """Test retrieving messages"""
        # Send multiple messages
        self.server.send_message("alice", "bob", "First")
        self.server.send_message("charlie", "bob", "Second")
        self.server.send_message("bob", "alice", "Reply")
        
        # Test getting all messages
        bob_messages = self.server.get_messages("bob")
        self.assertEqual(len(bob_messages), 2)
        self.assertEqual(bob_messages[0].content, "First")
        self.assertEqual(bob_messages[1].content, "Second")
        
        alice_messages = self.server.get_messages("alice")
        self.assertEqual(len(alice_messages), 1)
        self.assertEqual(alice_messages[0].content, "Reply")
        
        # Test invalid user
        with self.assertRaises(ValueError):
            self.server.get_messages("nonexistent")
    
    def test_mark_messages_read(self):
        """Test marking messages as read"""
        # Send messages
        msg1 = self.server.send_message("alice", "bob", "First")
        msg2 = self.server.send_message("charlie", "bob", "Second")
        
        # Verify initial unread count
        self.assertEqual(self.server.get_unread_count("bob"), 2)
        
        # Mark one message as read
        count = self.server.mark_messages_read("bob", [msg1.id])
        self.assertEqual(count, 1)
        self.assertEqual(self.server.get_unread_count("bob"), 1)
        
        # Mark both messages as read
        count = self.server.mark_messages_read("bob", [msg1.id, msg2.id])
        self.assertEqual(count, 1)  # Only one message was still unread
        self.assertEqual(self.server.get_unread_count("bob"), 0)
        
        # Test invalid user
        with self.assertRaises(ValueError):
            self.server.mark_messages_read("nonexistent", [msg1.id])
    
    def test_delete_messages(self):
        """Test deleting messages"""
        # Send messages
        msg1 = self.server.send_message("alice", "bob", "First")
        msg2 = self.server.send_message("bob", "alice", "Reply")
        
        # Delete as recipient
        self.server.delete_messages("bob", [msg1.id])
        messages = self.server.get_messages("bob")
        self.assertEqual(len(messages), 0)
        
        # Delete as sender
        self.server.delete_messages("bob", [msg2.id])
        messages = self.server.get_messages("alice")
        self.assertEqual(len(messages), 0)
        
        # Test invalid user
        with self.assertRaises(ValueError):
            self.server.delete_messages("nonexistent", [msg1.id])
    
    def test_message_ordering(self):
        """Test that messages are returned in chronological order"""
        # Send messages with different timestamps
        now = datetime.now()
        msg1 = Message(1, "alice", "bob", "First", now - timedelta(minutes=5))
        msg2 = Message(2, "alice", "bob", "Second", now)
        msg3 = Message(3, "alice", "bob", "Third", now - timedelta(minutes=10))
        
        # Add messages in random order
        self.server.messages.extend([msg2, msg3, msg1])
        
        # Get messages and verify order
        messages = self.server.get_messages("bob")
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0].content, "Third")  # Oldest
        self.assertEqual(messages[1].content, "First")
        self.assertEqual(messages[2].content, "Second")  # Newest

if __name__ == '__main__':
    unittest.main() 