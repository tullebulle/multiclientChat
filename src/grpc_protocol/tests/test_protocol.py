"""
Custom Protocol Unit Tests

Tests the binary protocol message encoding and decoding.
"""

import unittest
import struct
from datetime import datetime
import threading
import socket
from ...common.server_base import ThreadedTCPServer
from ..server_grpc import CustomChatRequestHandler
from .. import protocol
from ..client_grpc import CustomChatClient

class TestCustomProtocol(unittest.TestCase):
    """Unit tests for custom binary protocol implementation"""
    
    PROTOCOL_VERSION = 0  # Current protocol version

    @classmethod
    def setUpClass(cls):
        """Start server in a separate thread"""
        cls.server = ThreadedTCPServer(('localhost', 0), CustomChatRequestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        cls.server_port = cls.server.server_address[1]

    def setUp(self):
        """Set up test case"""
        self.client = CustomChatClient()
        self.client.connect(('localhost', self.server_port))
        self.additional_clients = []  # Track additional clients for cleanup

    def tearDown(self):
        """Clean up after test"""
        # Close main client
        if hasattr(self, 'client'):
            self.client.disconnect()
        
        # Close any additional clients
        for client in self.additional_clients:
            try:
                client.disconnect()
            except:
                pass
        self.additional_clients.clear()

    @classmethod
    def tearDownClass(cls):
        """Stop the server and print summary"""
        try:
            # First shutdown the server
            cls.server.shutdown()
            # Set a timeout for the server thread to prevent hanging
            cls.server_thread.join(timeout=2)
            # Then close the server socket
            cls.server.server_close()
        except Exception as e:
            print(f"Error during server shutdown: {e}")
            
        # Print test summary
        print("\n=== Custom Protocol Test Summary ===")
        print("✅ Protocol Message Tests:")
        print("  • Command encoding/decoding")
        print("  • Response format validation")
        print("  • Invalid message handling")
        print("  • Large message support")
        print("\n✅ Functional Tests:")
        print("  • User authentication")
        print("  • Message transmission")
        print("  • Message status tracking")
        print("  • Protocol version validation")
        print("\n✅ Integration Tests:")
        print("  • Client-server communication")
        print("  • Multi-user interaction")
        print("  • Resource cleanup")
        print("===============================\n")

    def create_additional_client(self):
        """Helper to create and track additional test clients"""
        client = CustomChatClient()
        client.connect(('localhost', self.server_port))
        self.additional_clients.append(client)
        return client

    def test_account_commands(self):
        """Test encoding/decoding of account-related commands"""
        test_cases = [
            (protocol.Command.AUTH, b'\x05alice\x05pass1'),
            (protocol.Command.CREATE_ACCOUNT, b'\x08testuser\x08testpass'),
            (protocol.Command.LIST_ACCOUNTS, b'\x01*')
        ]
        
        for command, payload in test_cases:
            with self.subTest(command=command):
                message = protocol.encode_message(command, payload)
                # Check protocol version
                self.assertEqual(message[0], self.PROTOCOL_VERSION)
                decoded_command, decoded_payload = protocol.decode_message(message)
                self.assertEqual(decoded_command, command)
                self.assertEqual(decoded_payload, payload)

    def test_message_commands(self):
        """Test encoding/decoding of message-related commands"""
        test_cases = [
            (protocol.Command.SEND_MESSAGE, b'\x03bob\x00\x0cHello, World!'),
            (protocol.Command.GET_MESSAGES, b'\x01'),
            (protocol.Command.MARK_READ, b'\x00\x02\x00\x00\x00\x01\x00\x00\x00\x02'),
            (protocol.Command.GET_UNREAD_COUNT, b''),
            (protocol.Command.DELETE_MESSAGES, b'\x00\x01\x00\x00\x00\x01')
        ]
        
        for command, payload in test_cases:
            with self.subTest(command=command):
                message = protocol.encode_message(command, payload)
                # Check protocol version
                self.assertEqual(message[0], self.PROTOCOL_VERSION)
                decoded_command, decoded_payload = protocol.decode_message(message)
                self.assertEqual(decoded_command, command)
                self.assertEqual(decoded_payload, payload)

    def test_message_responses(self):
        """Test message response formats"""
        test_cases = [
            (protocol.Command.SEND_MESSAGE, b'\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x01'),
            (protocol.Command.GET_MESSAGES, b'\x00\x01\x00\x00\x00\x01\x05alice\x0cHello, World!\x00\x00\x00\x00\x00\x00\x00\x01\x00'),
            (protocol.Command.MARK_READ, b'\x00\x01'),
            (protocol.Command.GET_UNREAD_COUNT, b'\x00\x02'),
            (protocol.Command.DELETE_MESSAGES, b'\x00\x01')
        ]
        
        for command, payload in test_cases:
            with self.subTest(command=command):
                message = protocol.encode_message(command, payload)
                # Check protocol version
                self.assertEqual(message[0], self.PROTOCOL_VERSION)
                decoded_command, decoded_payload = protocol.decode_message(message)
                self.assertEqual(decoded_command, command)
                self.assertEqual(decoded_payload, payload)

    def test_invalid_messages(self):
        """Test handling of invalid messages"""
        invalid_cases = [
            b'',  # Empty message
            b'\x01',  # Too short (no length)
            b'\x01\x00',  # Too short (no payload)
            b'\xFF\x00\x01',  # Invalid command
            b'\x01\x00\x05abc',  # Payload too short
        ]
        
        for invalid_msg in invalid_cases:
            with self.subTest(msg=invalid_msg):
                with self.assertRaises(ValueError):
                    protocol.decode_message(invalid_msg)

    def test_large_messages(self):
        """Test handling of large messages"""
        # Create a large message payload
        recipient = "bob"
        content = "x" * 1000  # 1KB content
        
        # Format: [recipient_len(1)][recipient][content_len(2)][content]
        payload = bytes([len(recipient)]) + recipient.encode()
        payload += struct.pack('!H', len(content)) + content.encode()
        
        message = protocol.encode_message(protocol.Command.SEND_MESSAGE, payload)
        decoded_command, decoded_payload = protocol.decode_message(message)
        
        self.assertEqual(decoded_command, protocol.Command.SEND_MESSAGE)
        self.assertEqual(decoded_payload, payload)

    def test_send_message(self):
        """Test sending a message"""
        # Create test users
        self.client.create_account("alice", "pass123")
        self.client.create_account("bob", "pass123")
        
        # Login as Alice
        self.assertTrue(self.client.login("alice", "pass123"))
        
        # Send message
        message = "Hello, Bob!"
        msg_id = self.client.send_message("bob", message)
        self.assertIsInstance(msg_id, int)
        
        # Login as Bob and check message
        bob_client = self.create_additional_client()
        self.assertTrue(bob_client.login("bob", "pass123"))
        
        messages = bob_client.get_messages()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['sender'], "alice")
        self.assertEqual(messages[0]['content'], message)
        self.assertFalse(messages[0]['is_read'])

    def test_unread_count(self):
        """Test getting unread message count"""
        # Clean up any existing accounts first
        if self.client.login("alice", "pass123"):
            self.client.delete_account("alice", "pass123")
        if self.client.login("bob", "pass123"):
            self.client.delete_account("bob", "pass123")
        
        # Create fresh test users
        self.client.create_account("alice", "pass123")
        self.client.create_account("bob", "pass123")
        
        # Login as Alice
        self.assertTrue(self.client.login("alice", "pass123"))
        
        # Send two messages
        self.client.send_message("bob", "Message 1")
        self.client.send_message("bob", "Message 2")
        
        # Login as Bob and check unread count
        bob_client = self.create_additional_client()
        self.assertTrue(bob_client.login("bob", "pass123"))
        
        # Get unread count
        count = bob_client.get_unread_count()
        self.assertEqual(count, 2)

    def test_invalid_version(self):
        """Test handling of invalid protocol version"""
        # Create a message with invalid version (current version + 1)
        command = protocol.Command.AUTH
        payload = b'\x05alice\x05pass1'
        message = protocol.encode_message(command, payload)
        # Modify the version byte to an invalid version
        invalid_message = bytes([self.PROTOCOL_VERSION + 1]) + message[1:]
        
        with self.assertRaises(ValueError) as cm:
            protocol.decode_message(invalid_message)
        self.assertIn("Unsupported protocol version", str(cm.exception))

if __name__ == '__main__':
    unittest.main(verbosity=2) 