"""
Integration Tests for Chat Application

This module tests the interaction between client and server components,
including network communication and protocol handling.
"""

import unittest
import threading
import socket
import time
from server import ThreadedTCPServer, ChatRequestHandler
import protocol
import json_protocol
import logging

class TestChatIntegration(unittest.TestCase):
    """Integration tests for the chat application"""

    @classmethod
    def setUpClass(cls):
        """Start server in a separate thread"""
        cls.server = ThreadedTCPServer(('localhost', 9999), ChatRequestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.5)  # Give more time for server to start

    @classmethod
    def tearDownClass(cls):
        """Shut down the server"""
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=1)

    def setUp(self):
        """Create a new client connection and clear server state for each test"""
        # Clear server state
        self.server.chat_server.users.clear()
        self.server.chat_server.online_users.clear()
        
        # Create new client connection
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect(('localhost', 9999))
        except Exception as e:
            self.fail(f"Could not connect to server: {e}")

    def tearDown(self):
        """Close the client connection"""
        try:
            self.client.shutdown(socket.SHUT_RDWR)
        except:
            pass  # Socket might already be closed
        self.client.close()

    def test_custom_protocol_account_creation(self):
        """Test account creation using custom protocol"""
        username = "testuser1"
        password = "testpass123"

        # Create payload: [username_length][username][password]
        payload = (
            bytes([len(username)]) +
            username.encode() +
            password.encode()
        )
        message = protocol.encode_message(protocol.Command.CREATE_ACCOUNT, payload)
        
        # Send message
        self.client.send(message)
        
        # Receive response
        response = self.client.recv(1024)
        command, payload = protocol.decode_message(response)
        
        # Check response
        self.assertEqual(command, protocol.Command.CREATE_ACCOUNT)
        self.assertEqual(payload, b'\x01')  # Success byte

    def test_json_protocol_account_creation(self):
        """Test account creation using JSON protocol"""
        payload = {
            "username": "testuser2",
            "password": "testpass123"
        }
        message = json_protocol.encode_message(
            json_protocol.Command.CREATE_ACCOUNT,
            payload
        )
        
        # Send message
        self.client.send(message)
        
        # Receive response
        response = self.client.recv(1024)
        command, payload = json_protocol.decode_message(response)
        
        # Check response
        self.assertEqual(command, json_protocol.Command.CREATE_ACCOUNT)
        self.assertEqual(payload["status"], "success")

    def test_authentication_flow(self):
        """Test full authentication flow with account creation"""
        # First create account
        username = "testuser3"
        password = "testpass123"
        
        create_payload = {
            "username": username,
            "password": password
        }
        message = json_protocol.encode_message(
            json_protocol.Command.CREATE_ACCOUNT,
            create_payload
        )
        self.client.send(message)
        self.client.recv(1024)  # Clear creation response
        
        # Then try to authenticate
        auth_payload = {
            "username": username,
            "password_hash": password  # In real app, this would be hashed
        }
        message = json_protocol.encode_message(
            json_protocol.Command.AUTH,
            auth_payload
        )
        self.client.send(message)
        
        # Check auth response
        response = self.client.recv(1024)
        command, payload = json_protocol.decode_message(response)
        self.assertEqual(command, json_protocol.Command.AUTH)
        self.assertEqual(payload["status"], "success")

    def test_invalid_authentication(self):
        """Test authentication with invalid credentials"""
        payload = {
            "username": "nonexistent",
            "password_hash": "wrongpass"
        }
        message = json_protocol.encode_message(
            json_protocol.Command.AUTH,
            payload
        )
        self.client.send(message)
        
        # Check response
        response = self.client.recv(1024)
        command, payload = json_protocol.decode_message(response)
        self.assertEqual(command, json_protocol.Command.AUTH)
        self.assertEqual(payload["status"], "error")

    def test_protocol_error_handling(self):
        """Test server's handling of malformed messages"""
        # Send invalid data
        self.client.send(b"invalid data")
        
        # Should receive error response
        response = self.client.recv(1024)
        try:
            # Try JSON protocol first
            command, payload = json_protocol.decode_message(response)
            self.assertEqual(payload["status"], "error")
        except:
            # Fall back to custom protocol
            command, payload = protocol.decode_message(response)
            self.assertEqual(command, protocol.Command.ERROR)


    ########## TESTING THE LIST ACCOUNTS COMMAND ##########

    def test_list_accounts_empty(self):
        """Test listing accounts when none exist"""
        payload = {
            "pattern": "*"  # Match all accounts
        }
        message = json_protocol.encode_message(
            json_protocol.Command.LIST_ACCOUNTS,
            payload
        )
        self.client.send(message)
        
        # Check response
        response = self.client.recv(1024)
        command, payload = json_protocol.decode_message(response)
        self.assertEqual(command, json_protocol.Command.LIST_ACCOUNTS)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["accounts"], [])

    def test_list_accounts_with_pattern(self):
        """Test listing accounts with wildcard pattern matching"""
        # Create some test accounts first
        test_accounts = [
            ("test_user1", "pass123"),
            ("test_user2", "pass123"),
            ("other_user", "pass123"),
            ("admin_user", "pass123")
        ]
        
        for username, password in test_accounts:
            create_payload = {
                "username": username,
                "password": password
            }
            message = json_protocol.encode_message(
                json_protocol.Command.CREATE_ACCOUNT,
                create_payload
            )
            self.client.send(message)
            self.client.recv(1024)  # Clear creation response
        
        # Test different patterns
        patterns = {
            "test_*": ["test_user1", "test_user2"],
            "*user*": ["test_user1", "test_user2", "other_user", "admin_user"],
            "admin_*": ["admin_user"],
            "nonexistent*": []
        }
        
        for pattern, expected in patterns.items():
            with self.subTest(pattern=pattern):
                payload = {"pattern": pattern}
                message = json_protocol.encode_message(
                    json_protocol.Command.LIST_ACCOUNTS,
                    payload
                )
                self.client.send(message)
                
                response = self.client.recv(1024)
                command, payload = json_protocol.decode_message(response)
                self.assertEqual(command, json_protocol.Command.LIST_ACCOUNTS)
                self.assertEqual(payload["status"], "success")
                self.assertEqual(sorted(payload["accounts"]), sorted(expected))

    def test_list_accounts_pagination(self):
        """Test account listing with pagination"""
        # Clear any existing accounts first
        self.client.send(json_protocol.encode_message(
            json_protocol.Command.LIST_ACCOUNTS,
            {"pattern": "*", "page": 1, "page_size": 1000}  # Get all accounts
        ))
        self.client.recv(1024)  # Clear response
        
        # Create exactly 25 test accounts
        for i in range(25):
            create_payload = {
                "username": f"user{i:02d}",
                "password": "pass123"
            }
            message = json_protocol.encode_message(
                json_protocol.Command.CREATE_ACCOUNT,
                create_payload
            )
            self.client.send(message)
            self.client.recv(1024)  # Clear creation response
        
        # Test pagination
        page_tests = [
            # page, page_size, expected_count
            (1, 10, 10),    # First page
            (2, 10, 10),    # Second page
            (3, 10, 5),     # Last page
            (4, 10, 0),     # Empty page
            (1, 20, 20),    # Larger page size
            (1, 30, 25),    # Page size larger than total
        ]
        
        for page, page_size, expected_count in page_tests:
            with self.subTest(pattern=f"page={page}, size={page_size}"):
                payload = {
                    "pattern": "*",
                    "page": page,
                    "page_size": page_size
                }
                message = json_protocol.encode_message(
                    json_protocol.Command.LIST_ACCOUNTS,
                    payload
                )
                self.client.send(message)
                
                response = self.client.recv(1024)
                command, payload = json_protocol.decode_message(response)
                self.assertEqual(command, json_protocol.Command.LIST_ACCOUNTS)
                self.assertEqual(payload["status"], "success")
                self.assertEqual(len(payload["accounts"]), expected_count)
                self.assertEqual(payload["total_accounts"], 25)
                self.assertEqual(payload["total_pages"], 
                               (25 + page_size - 1) // page_size)

    def test_list_accounts_custom_protocol(self):
        """Test listing accounts using custom protocol"""
        # Create test account
        username = "testuser"
        password = "testpass123"
        create_payload = (
            bytes([len(username)]) +
            username.encode() +
            password.encode()
        )
        message = protocol.encode_message(protocol.Command.CREATE_ACCOUNT, create_payload)
        self.client.send(message)
        self.client.recv(1024)  # Clear creation response
        
        # Test listing accounts
        pattern = "*user*"
        payload = bytes([len(pattern)]) + pattern.encode()
        message = protocol.encode_message(protocol.Command.LIST_ACCOUNTS, payload)
        self.client.send(message)
        
        response = self.client.recv(1024)
        command, payload = protocol.decode_message(response)
        self.assertEqual(command, protocol.Command.LIST_ACCOUNTS)
        
        # First byte is number of accounts
        num_accounts = payload[0]
        self.assertEqual(num_accounts, 1)
        
        # Rest is account names
        account_len = payload[1]
        account_name = payload[2:2+account_len].decode('utf-8')
        self.assertEqual(account_name, username)

if __name__ == '__main__':
    # Reduce logging noise during tests
    logging.getLogger().setLevel(logging.ERROR)
    unittest.main(verbosity=2) 