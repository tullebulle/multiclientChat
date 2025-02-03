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
        """Create a new client connection for each test"""
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

if __name__ == '__main__':
    # Reduce logging noise during tests
    logging.getLogger().setLevel(logging.ERROR)
    unittest.main(verbosity=2) 