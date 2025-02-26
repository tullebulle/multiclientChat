"""
Integration tests for the gRPC chat system.
"""

import unittest
import grpc
import time
import threading
from concurrent import futures
import logging

from .. import chat_pb2
from .. import chat_pb2_grpc
from .. import client
from .. import server

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestGRPCChatIntegration(unittest.TestCase):
    """Integration tests for gRPC chat implementation"""

    @classmethod
    def setUpClass(cls):
        """Start the server in a separate thread"""
        # Create and start server
        cls.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        cls.service = server.ChatServicer()
        chat_pb2_grpc.add_ChatServiceServicer_to_server(cls.service, cls.server)
        cls.server.add_insecure_port('[::]:50051')
        cls.server.start()
        print("\nServer started for integration tests")

    @classmethod
    def tearDownClass(cls):
        """Stop the server"""
        cls.server.stop(grace=None)
        print("\nServer stopped")

    def setUp(self):
        """Create a new client for each test"""
        logger.info("Setting up new test")
        self.client = client.GRPCChatClient(host='localhost', port=50051)
        connected = self.client.connect()
        logger.info(f"Client connected: {connected}")
        
        # Clear server state
        self.service.messages = []
        self.service.accounts = {}
        logger.info("Cleared server state")

    def tearDown(self):
        """Clean up after each test"""
        self.client.disconnect()

    def test_create_and_login(self):
        """Test account creation and login"""
        logger.info("Testing account creation and login")
        
        # Log the actual return value
        result = self.client.create_account("testuser1", "password123")
        logger.info(f"create_account returned: {result}")
        self.assertTrue(result, "Failed to create account")

        # Log the actual return value
        result = self.client.login("testuser1", "password123")
        logger.info(f"login returned: {result}")
        self.assertTrue(result, "Failed to login")

    def test_send_and_receive_message(self):
        """Test sending and receiving messages between two users"""
        logger.info("Testing message sending and receiving")
        
        # Create two users
        result = self.client.create_account("sender", "password123")
        logger.info(f"create_account(sender) returned: {result}")
        self.assertTrue(result[0], "Failed to create sender account")
        
        result = self.client.create_account("receiver", "password123")
        logger.info(f"create_account(receiver) returned: {result}")
        self.assertTrue(result[0], "Failed to create receiver account")

        # Login as sender - returns bool
        result = self.client.login("sender", "password123")
        logger.info(f"login(sender) returned: {result}")
        self.assertTrue(result, "Failed to login as sender")

        # Send a message - returns (id, error)
        msg_id = self.client.send_message("receiver", "Hello, receiver!")[0]  # Get just the ID
        logger.info(f"send_message returned msg_id: {msg_id}")
        self.assertGreater(msg_id, 0, "Failed to send message")

        # Login as receiver
        result = self.client.login("receiver", "password123")
        logger.info(f"login(receiver) returned: {result}")
        self.assertTrue(result, "Failed to login as receiver")

        # Get messages - returns list
        messages = self.client.get_messages()
        logger.info(f"get_messages returned: {messages}")
        self.assertEqual(len(messages), 1, "Wrong number of messages received")
        self.assertEqual(messages[0]['sender'], "sender")
        self.assertEqual(messages[0]['content'], "Hello, receiver!")
        self.assertFalse(messages[0]['is_read'])

    def test_list_accounts(self):
        """Test listing user accounts"""
        # Create test accounts
        usernames = ["user1", "user2", "user3"]
        for username in usernames:
            success, error = self.client.create_account(username, "password123")
            self.assertTrue(success, f"Failed to create account {username}: {error}")

        # List accounts - returns list[str]
        accounts = self.client.list_accounts()
        self.assertEqual(sorted(accounts), sorted(usernames), "Account list doesn't match")

    def test_delete_account(self):
        """Test account deletion"""
        # Create and login
        username = "deletetest"
        success, error = self.client.create_account(username, "password123")
        self.assertTrue(success, f"Failed to create account: {error}")
        
        # Delete account returns bool
        success = self.client.delete_account(username, "password123")
        self.assertTrue(success, "Failed to delete account")
        
        # Verify account is gone
        accounts = self.client.list_accounts()
        self.assertNotIn(username, accounts, "Account still exists after deletion")

    def test_mark_messages_as_read(self):
        """Test marking messages as read"""
        # Setup users
        success, error = self.client.create_account("sender", "password123")
        self.assertTrue(success, f"Failed to create sender account: {error}")
        success, error = self.client.create_account("reader", "password123")
        self.assertTrue(success, f"Failed to create reader account: {error}")
        
        success = self.client.login("sender", "password123")
        self.assertTrue(success, "Failed to login as sender")
        
        # Send message
        msg_id, error = self.client.send_message("reader", "Read me!")
        self.assertGreater(msg_id, 0, f"Failed to send message: {error}")
        
        # Login as reader
        success = self.client.login("reader", "password123")
        self.assertTrue(success, "Failed to login as reader")
        
        # Check message is unread
        messages = self.client.get_messages()
        self.assertFalse(messages[0]['is_read'])
        
        # Mark as read returns bool
        success = self.client.mark_read([msg_id])
        self.assertTrue(success)
        
        # Verify message is now read
        messages = self.client.get_messages()
        self.assertTrue(messages[0]['is_read'])

    def test_duplicate_account_creation(self):
        """Test creating account with existing username"""
        # Create first account
        success, _ = self.client.create_account("testuser2", "password123")
        self.assertTrue(success)

        # Try to create duplicate account
        success, error = self.client.create_account("testuser2", "different_password")
        self.assertFalse(success)
        self.assertEqual(error, "Username already exists")

    def test_delete_messages(self):
        """Test message deletion"""
        logger.info("Testing message deletion")
        
        # Setup users and messages
        self.client.create_account("sender", "password123")
        self.client.create_account("receiver", "password123")
        self.client.login("sender", "password123")
        
        # Send test messages
        msg_id = self.client.send_message("receiver", "Test message")[0]  # Get just the ID
        logger.info(f"Sent message with ID: {msg_id}")
        
        # Login as receiver
        self.client.login("receiver", "password123")
        
        # Get initial messages
        messages = self.client.get_messages()  # Returns list directly
        logger.info(f"Initial messages: {messages}")
        self.assertEqual(len(messages), 1)
        
        # Delete message
        success = self.client.delete_messages([msg_id])
        logger.info(f"Delete message result: {success}")
        self.assertTrue(success)
        
        # Verify deletion
        messages = self.client.get_messages()
        logger.info(f"Messages after deletion: {messages}")
        self.assertEqual(len(messages), 0)

    def test_concurrent_messages(self):
        """Test handling concurrent message sending"""
        logger.info("Testing concurrent message handling")
        
        # Setup users
        self.client.create_account("sender1", "password123")
        self.client.create_account("sender2", "password123")
        self.client.create_account("receiver", "password123")
        
        # Send messages from both senders
        self.client.login("sender1", "password123")
        msg1_id = self.client.send_message("receiver", "Message 1")[0]
        
        self.client.login("sender2", "password123")
        msg2_id = self.client.send_message("receiver", "Message 2")[0]
        
        # Check messages as receiver
        self.client.login("receiver", "password123")
        messages = self.client.get_messages()  # Returns list directly
        self.assertEqual(len(messages), 2)
        
        # Verify both messages received
        message_contents = {msg['content'] for msg in messages}
        self.assertEqual(message_contents, {"Message 1", "Message 2"})

    def test_unread_messages_filter(self):
        """Test filtering unread messages"""
        logger.info("Testing unread message filtering")
        
        # Setup users
        self.client.create_account("sender", "password123")
        self.client.create_account("receiver", "password123")
        
        # Send messages
        self.client.login("sender", "password123")
        msg_ids = []
        for i in range(3):
            msg_id = self.client.send_message("receiver", f"Message {i}")[0]
            msg_ids.append(msg_id)
            logger.info(f"Sent message {i} with ID: {msg_id}")
        
        # Login as receiver
        self.client.login("receiver", "password123")
        
        # Mark some messages as read
        self.client.mark_read(msg_ids[:1])
        logger.info("Marked first message as read")
        
        # Get unread messages
        messages = self.client.get_messages(include_read=False)  # Returns list directly
        logger.info(f"Unread messages: {messages}")
        self.assertEqual(len(messages), 2)  # Should only see unread messages

    def test_send_message_to_nonexistent_user(self):
        """Test sending a message to a user that doesn't exist"""
        # Create and login as sender
        self.client.create_account("sender", "password123")
        self.client.login("sender", "password123")
        
        # Try to send message to nonexistent user
        msg_id, error = self.client.send_message("nonexistent", "Hello!")
        self.assertEqual(msg_id, 0)
        self.assertEqual(error, "Recipient does not exist")

    def test_unauthorized_message_access(self):
        """Test that users can't access others' messages"""
        logger.info("Testing unauthorized message access")
        
        # Setup users
        self.client.create_account("sender", "password123")
        self.client.create_account("receiver", "password123")
        self.client.create_account("hacker", "password123")
        
        # Send message
        self.client.login("sender", "password123")
        msg_id = self.client.send_message("receiver", "Secret message")[0]
        logger.info(f"Sent message with ID: {msg_id}")
        
        # Try to access as unauthorized user
        self.client.login("hacker", "password123")
        messages = self.client.get_messages()  # Returns list directly
        logger.info(f"Messages visible to hacker: {messages}")
        self.assertEqual(len(messages), 0)

    def test_message_ordering(self):
        """Test that messages are returned in order"""
        logger.info("Testing message ordering")
        
        # Setup users
        self.client.create_account("sender", "password123")
        self.client.create_account("receiver", "password123")
        self.client.login("sender", "password123")
        
        # Send messages with different timestamps
        msg_ids = []
        for i in range(3):
            msg_id = self.client.send_message("receiver", f"Message {i}")[0]
            msg_ids.append(msg_id)
            logger.info(f"Sent message {i} with ID: {msg_id}")
        
        # Login as receiver
        self.client.login("receiver", "password123")
        
        # Get messages
        messages = self.client.get_messages()  # Returns list directly
        logger.info(f"Retrieved messages: {messages}")
        
        # Verify order
        timestamps = [msg['timestamp'] for msg in messages]
        self.assertEqual(timestamps, sorted(timestamps))

    def test_invalid_login_attempts(self):
        """Test invalid login scenarios"""
        logger.info("Testing invalid login attempts")
        
        # Create test account
        result = self.client.create_account("user", "password123")
        logger.info(f"create_account returned: {result}")
        self.assertTrue(result[0], "Failed to create account")
        
        # Test wrong password - returns bool
        success = self.client.login("user", "wrongpass")
        logger.info(f"login with wrong password returned: {success}")
        self.assertFalse(success)
        
        # Test non-existent user - returns bool
        success = self.client.login("nonexistent", "password123")
        logger.info(f"login with nonexistent user returned: {success}")
        self.assertFalse(success)

    def test_empty_message_handling(self):
        """Test handling of empty messages"""
        # Create and login user
        self.client.create_account("sender", "password123")
        self.client.create_account("receiver", "password123")
        self.client.login("sender", "password123")
        
        # Try to send empty message
        msg_id, error = self.client.send_message("receiver", "")
        self.assertEqual(msg_id, 0)
        self.assertEqual(error, "Message content cannot be empty")

    def test_bulk_message_operations(self):
        """Test bulk message operations (mark read, delete)"""
        logger.info("Testing bulk message operations")
        
        # Create test users and messages
        self.client.create_account("sender", "password123")
        self.client.create_account("receiver", "password123")
        self.client.login("sender", "password123")
        
        # Send multiple messages
        msg_ids = []
        for i in range(5):
            msg_id = self.client.send_message("receiver", f"Message {i}")[0]  # Get just the ID
            msg_ids.append(msg_id)
        
        # Login as receiver
        self.client.login("receiver", "password123")
        
        # Get initial messages
        messages = self.client.get_messages()  # Returns list directly
        self.assertEqual(len(messages), 5)
        
        # Mark some messages as read
        success = self.client.mark_read(msg_ids[:3])
        self.assertTrue(success)
        
        # Verify read status
        messages = self.client.get_messages()
        read_count = sum(1 for msg in messages if msg['is_read'])
        self.assertEqual(read_count, 3)

    def test_reconnection(self):
        """Test client reconnection"""
        logger.info("Testing client reconnection")
        
        # Create test account
        self.client.create_account("user", "password123")
        
        # Initial login
        success = self.client.login("user", "password123")  # Returns bool
        self.assertTrue(success)
        
        # Simulate disconnect and reconnect
        self.client.disconnect()
        self.client.connect()
        
        # Try login again
        success = self.client.login("user", "password123")
        self.assertTrue(success)

if __name__ == '__main__':
    unittest.main() 