"""
JSON Protocol Integration Tests

Tests the interaction between JSON protocol client and server.
"""

import unittest
import threading
import socket
import time
from datetime import datetime
from ...common.server_base import ThreadedTCPServer
from ..server import JSONChatRequestHandler
from .. import protocol

class TestJSONIntegration(unittest.TestCase):
    """Integration tests for JSON protocol"""

    @classmethod
    def setUpClass(cls):
        """Start server in a separate thread"""
        cls.server = ThreadedTCPServer(('localhost', 0), JSONChatRequestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        cls.server_port = cls.server.server_address[1]

    def setUp(self):
        """Create test users and establish client connection"""
        # Clear server state
        self.server.chat_server.users.clear()
        self.server.chat_server.messages.clear()
        
        # Create test users directly on server
        self.server.chat_server.create_account("alice", "pass1")
        self.server.chat_server.create_account("bob", "pass2")
        
        # Connect client
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(('localhost', self.server_port))
        
        # Login as Alice
        self.login_alice()

    def tearDown(self):
        """Clean up client connection"""
        self.client.close()

    def login_alice(self):
        """Helper to log in as Alice"""
        payload = {
            "username": "alice",
            "password_hash": "pass1"
        }
        self.send_command(protocol.Command.AUTH, payload)

    def send_command(self, command, payload):
        """Helper to send a command and get response"""
        message = protocol.encode_message(command, payload)
        self.client.sendall(message)
        response = self.client.recv(4096)
        return protocol.decode_message(response)

    def test_create_account(self):
        """Test account creation"""
        payload = {
            "username": "testuser",
            "password": "testpass"
        }
        cmd, response = self.send_command(protocol.Command.CREATE_ACCOUNT, payload)
        
        self.assertEqual(cmd, protocol.Command.CREATE_ACCOUNT.name)
        self.assertEqual(response["status"], "success")
        
        # Test duplicate username
        cmd, response = self.send_command(protocol.Command.CREATE_ACCOUNT, payload)
        self.assertEqual(response["status"], "error")

    def test_authentication(self):
        """Test user authentication"""
        # Test valid credentials
        payload = {
            "username": "alice",
            "password_hash": "pass1"
        }
        cmd, response = self.send_command(protocol.Command.AUTH, payload)
        self.assertEqual(response["status"], "success")
        
        # Test invalid credentials
        payload["password_hash"] = "wrongpass"
        cmd, response = self.send_command(protocol.Command.AUTH, payload)
        self.assertEqual(response["status"], "error")

    def test_list_accounts(self):
        """Test account listing with pagination"""
        # Create additional test accounts
        for i in range(25):
            payload = {
                "username": f"user{i:02d}",
                "password": "testpass"
            }
            self.send_command(protocol.Command.CREATE_ACCOUNT, payload)
        
        # Test pagination
        payload = {
            "pattern": "*",
            "page": 1,
            "page_size": 10
        }
        cmd, response = self.send_command(protocol.Command.LIST_ACCOUNTS, payload)
        
        self.assertEqual(cmd, protocol.Command.LIST_ACCOUNTS.name)
        self.assertEqual(response["status"], "success")
        self.assertEqual(len(response["accounts"]), 10)
        self.assertEqual(response["total_pages"], 3)
        self.assertEqual(response["total_accounts"], 27)  # 25 + alice + bob

    def test_send_message(self):
        """Test sending a message"""
        payload = {
            "recipient": "bob",
            "content": "Hello, Bob!"
        }
        cmd, response = self.send_command(protocol.Command.SEND_MESSAGE, payload)
        
        self.assertEqual(cmd, protocol.Command.SEND_MESSAGE.name)
        self.assertEqual(response["status"], "success")
        self.assertIn("message_id", response)
        self.assertIn("timestamp", response)

    def test_get_messages(self):
        """Test retrieving messages"""
        # Send a message first
        self.send_command(
            protocol.Command.SEND_MESSAGE,
            {"recipient": "bob", "content": "First message"}
        )
        
        # Get messages
        cmd, response = self.send_command(
            protocol.Command.GET_MESSAGES,
            {"include_read": True}
        )
        
        self.assertEqual(cmd, protocol.Command.GET_MESSAGES.name)
        self.assertEqual(response["status"], "success")
        self.assertIn("messages", response)
        self.assertTrue(isinstance(response["messages"], list))

    def test_unread_count(self):
        """Test getting unread message count"""
        # Send messages
        self.send_command(
            protocol.Command.SEND_MESSAGE,
            {"recipient": "bob", "content": "Message 1"}
        )
        self.send_command(
            protocol.Command.SEND_MESSAGE,
            {"recipient": "bob", "content": "Message 2"}
        )
        
        # Login as Bob in a new connection
        bob_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        bob_client.connect(('localhost', self.server_port))
        
        # Auth as Bob
        auth_message = protocol.encode_message(
            protocol.Command.AUTH,
            {"username": "bob", "password_hash": "pass2"}
        )
        bob_client.sendall(auth_message)
        bob_client.recv(4096)  # Get auth response
        
        # Get unread count
        count_message = protocol.encode_message(
            protocol.Command.GET_UNREAD_COUNT,
            {}
        )
        bob_client.sendall(count_message)
        _, response = protocol.decode_message(bob_client.recv(4096))
        
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["count"], 2)
        
        bob_client.close()

    def test_mark_read(self):
        """Test marking messages as read"""
        # Send a message
        _, send_response = self.send_command(
            protocol.Command.SEND_MESSAGE,
            {"recipient": "bob", "content": "Test message"}
        )
        message_id = send_response["message_id"]
        
        # Login as Bob and mark as read
        bob_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        bob_client.connect(('localhost', self.server_port))
        
        # Auth as Bob
        auth_message = protocol.encode_message(
            protocol.Command.AUTH,
            {"username": "bob", "password_hash": "pass2"}
        )
        bob_client.sendall(auth_message)
        bob_client.recv(4096)  # Get auth response
        
        # Mark as read
        mark_message = protocol.encode_message(
            protocol.Command.MARK_READ,
            {"message_ids": [message_id]}
        )
        bob_client.sendall(mark_message)
        _, response = protocol.decode_message(bob_client.recv(4096))
        
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["marked_count"], 1)
        
        bob_client.close()

    def test_unauthorized_access(self):
        """Test unauthorized access to messages"""
        # Create a new connection without logging in
        unauth_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        unauth_client.connect(('localhost', self.server_port))
        
        # Try to send a message without auth
        message = protocol.encode_message(
            protocol.Command.SEND_MESSAGE,
            {"recipient": "bob", "content": "Unauthorized message"}
        )
        unauth_client.sendall(message)
        _, response = protocol.decode_message(unauth_client.recv(4096))
        
        self.assertEqual(response["status"], "error")
        self.assertIn("Not authenticated", response["message"])
        
        unauth_client.close()

if __name__ == '__main__':
    unittest.main(verbosity=2) 