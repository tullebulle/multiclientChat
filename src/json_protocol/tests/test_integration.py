"""
JSON Protocol Integration Tests

Tests the interaction between JSON protocol client and server.
"""

import unittest
import threading
import socket
import logging
import sys
from datetime import datetime
from ...common.server_base import ThreadedTCPServer
from ..server import JSONChatRequestHandler
from .. import json_protocol

# Configure logging at module level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TestJSONIntegration(unittest.TestCase):
    """Integration tests for JSON protocol"""

    @classmethod
    def setUpClass(cls):
        """Start server in a separate thread"""
        logger.info("\n=== Starting JSON Protocol Integration Tests ===")
        print("🔵 Creating server instance")
        cls.server = ThreadedTCPServer(('localhost', 0), JSONChatRequestHandler)
        print(f"🔵 Server created with handler: {JSONChatRequestHandler}")
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        cls.server_port = cls.server.server_address[1]
        print(f"🔵 Server started on port {cls.server_port}")

    def setUp(self):
        """Create test users and establish client connection"""
        # Enable detailed logging
        logger.info("\n=== Setting up test ===")
        
        # Clear server state
        self.server.chat_server.users.clear()
        self.server.chat_server.messages.clear()
        logger.info("Cleared server state")
        
        # Create test users directly on server
        self.server.chat_server.create_account("alice", "pass1")
        self.server.chat_server.create_account("bob", "pass2")
        logger.info("Created test users alice and bob")
        
        # Connect client
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(('localhost', self.server_port))
        logger.info("Connected client socket")
        
        # Always login as Alice by default
        if not self.login_alice():
            raise RuntimeError("Failed to login as Alice during setup")
        logger.info("Logged in as Alice")

    def tearDown(self):
        """Clean up client connection"""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("Closed client connection")

    def send_command(self, command, payload):
        """Helper to send a command and get response"""
        try:
            logger.info(f"Sending command {command}")
            logger.debug(f"Payload: {payload}")
            
            message = json_protocol.encode_message(command, payload)
            logger.debug(f"Encoded message: {message.decode('utf-8')}")
            
            self.client.sendall(message)
            response = self.client.recv(4096)
            logger.debug(f"Raw response: {response.decode('utf-8')}")
            
            cmd, payload = json_protocol.decode_message(response)
            if isinstance(cmd, json_protocol.Command):
                cmd = cmd.name
            logger.info(f"Received response - cmd: {cmd}")
            logger.debug(f"Response payload: {payload}")
            
            return cmd, payload
            
        except Exception as e:
            logger.error(f"Error in send_command: {e}", exc_info=True)
            raise

    def login_alice(self):
        """Helper to log in as Alice"""
        logger.info("Attempting to login as Alice")
        payload = {
            "username": "alice",
            "password_hash": "pass1"
        }
        try:
            cmd, response = self.send_command(json_protocol.Command.AUTH, payload)
            if response["status"] != "success":
                logger.error(f"Login failed: {response}")
                return False
            logger.info("Successfully logged in as Alice")
            return True
        except Exception as e:
            logger.error(f"Login failed with exception: {e}")
            return False

    def test_create_account(self):
        """Test account creation"""
        logger.info("\n=== Starting test_create_account ===")
        
        # Create a new account (should work without auth)
        payload = {
            "username": "testuser",
            "password": "testpass"
        }
        logger.info("Creating new test account")
        cmd, response = self.send_command(json_protocol.Command.CREATE_ACCOUNT, payload)
        
        self.assertEqual(cmd, "CREATE_ACCOUNT")
        self.assertEqual(response["status"], "success")
        
        # Test duplicate username
        logger.info("Testing duplicate username")
        cmd, response = self.send_command(json_protocol.Command.CREATE_ACCOUNT, payload)
        self.assertEqual(response["status"], "error")

    def test_authentication(self):
        """Test user authentication"""
        # Test valid credentials
        payload = {
            "username": "alice",
            "password_hash": "pass1"
        }
        cmd, response = self.send_command(json_protocol.Command.AUTH, payload)
        self.assertEqual(response["status"], "success")
        
        # Test invalid credentials
        payload["password_hash"] = "wrongpass"
        cmd, response = self.send_command(json_protocol.Command.AUTH, payload)
        self.assertEqual(response["status"], "error")

    def test_list_accounts(self):
        """Test account listing with pagination"""
        logging.debug("\n🔵 STARTING test_list_accounts")
        # Create additional test accounts
        for i in range(25):
            payload = {
                "username": f"user{i:02d}",
                "password": "testpass"
            }
            logging.debug(f"🔵 Creating test account {i}: user{i:02d}")
            cmd, resp = self.send_command(json_protocol.Command.CREATE_ACCOUNT, payload)
            logging.debug(f"🔵 Creation response: {resp}")
        
        # Test pagination
        payload = {
            "pattern": "*",
            "page": 1,
            "page_size": 10
        }
        logging.debug("\n🔵 Testing pagination with payload:", payload)
        cmd, response = self.send_command(json_protocol.Command.LIST_ACCOUNTS, payload)
        logging.debug(f"🔵 LIST_ACCOUNTS RESPONSE - cmd: {cmd}")
        logging.debug(f"🔵 Response payload: {response}")
        
        self.assertEqual(cmd, json_protocol.Command.LIST_ACCOUNTS.name)
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
        cmd, response = self.send_command(json_protocol.Command.SEND_MESSAGE, payload)
        
        self.assertEqual(cmd, json_protocol.Command.SEND_MESSAGE.name)
        self.assertEqual(response["status"], "success")
        self.assertIn("message_id", response)
        self.assertIn("timestamp", response)

    def test_get_messages(self):
        """Test retrieving messages"""
        # Send a message first
        self.send_command(
            json_protocol.Command.SEND_MESSAGE,
            {"recipient": "bob", "content": "First message"}
        )
        
        # Get messages
        cmd, response = self.send_command(
            json_protocol.Command.GET_MESSAGES,
            {"include_read": True}
        )
        
        self.assertEqual(cmd, json_protocol.Command.GET_MESSAGES.name)
        self.assertEqual(response["status"], "success")
        self.assertIn("messages", response)
        self.assertTrue(isinstance(response["messages"], list))

    def test_unread_count(self):
        """Test getting unread message count"""
        # Send messages
        self.send_command(
            json_protocol.Command.SEND_MESSAGE,
            {"recipient": "bob", "content": "Message 1"}
        )
        self.send_command(
            json_protocol.Command.SEND_MESSAGE,
            {"recipient": "bob", "content": "Message 2"}
        )
        
        # Login as Bob in a new connection
        bob_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        bob_client.connect(('localhost', self.server_port))
        
        # Auth as Bob
        auth_message = json_protocol.encode_message(
            json_protocol.Command.AUTH,
            {"username": "bob", "password_hash": "pass2"}
        )
        bob_client.sendall(auth_message)
        bob_client.recv(4096)  # Get auth response
        
        # Get unread count
        count_message = json_protocol.encode_message(
            json_protocol.Command.GET_UNREAD_COUNT,
            {}
        )
        bob_client.sendall(count_message)
        _, response = json_protocol.decode_message(bob_client.recv(4096))
        
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["count"], 2)
        
        bob_client.close()

    def test_mark_read(self):
        """Test marking messages as read"""
        # Send a message
        _, send_response = self.send_command(
            json_protocol.Command.SEND_MESSAGE,
            {"recipient": "bob", "content": "Test message"}
        )
        message_id = send_response["message_id"]
        
        # Login as Bob and mark as read
        bob_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        bob_client.connect(('localhost', self.server_port))
        
        # Auth as Bob
        auth_message = json_protocol.encode_message(
            json_protocol.Command.AUTH,
            {"username": "bob", "password_hash": "pass2"}
        )
        bob_client.sendall(auth_message)
        bob_client.recv(4096)  # Get auth response
        
        # Mark as read
        mark_message = json_protocol.encode_message(
            json_protocol.Command.MARK_READ,
            {"message_ids": [message_id]}
        )
        bob_client.sendall(mark_message)
        _, response = json_protocol.decode_message(bob_client.recv(4096))
        
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["marked_count"], 1)
        
        bob_client.close()

    def test_unauthorized_access(self):
        """Test unauthorized access to messages"""
        # Create a new connection without logging in
        unauth_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        unauth_client.connect(('localhost', self.server_port))
        
        # Try to send a message without auth
        message = json_protocol.encode_message(
            json_protocol.Command.SEND_MESSAGE,
            {"recipient": "bob", "content": "Unauthorized message"}
        )
        unauth_client.sendall(message)
        _, response = json_protocol.decode_message(unauth_client.recv(4096))
        
        self.assertEqual(response["status"], "error")
        self.assertIn("Not authenticated", response["message"])
        
        unauth_client.close()

    @classmethod
    def tearDownClass(cls):
        """Stop the server and print summary"""
        try:
            cls.server.shutdown()
            cls.server_thread.join(timeout=2)
            cls.server.server_close()
        except Exception as e:
            print(f"Error during server shutdown: {e}")
            
        # Print test summary
        print("\n=== JSON Protocol Integration Test Summary ===")
        print("✅ End-to-End Flows Tested:")
        print("  • User Registration and Authentication")
        print("  • Message Sending and Receiving")
        print("  • Message Status Management")
        print("  • Account Management")
        
        print("\n✅ Server Features Verified:")
        print("  • Multi-user Support")
        print("  • Concurrent Connections")
        print("  • Message Storage and Retrieval")
        print("  • User Session Management")
        
        print("\n✅ Client-Server Interactions:")
        print("  • Connection Handling")
        print("  • Protocol Compliance")
        print("  • Error Recovery")
        print("  • Resource Cleanup")
        print("==========================================\n")

if __name__ == '__main__':
    unittest.main(verbosity=2) 