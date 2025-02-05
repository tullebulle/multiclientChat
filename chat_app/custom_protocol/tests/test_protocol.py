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
from ..server import CustomChatRequestHandler
from .. import protocol

class TestCustomProtocol(unittest.TestCase):
    """Unit tests for custom binary protocol implementation"""

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
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(('localhost', self.server_port))

    def tearDown(self):
        """Clean up after test"""
        self.client.close()

    @classmethod
    def tearDownClass(cls):
        """Stop the server"""
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join()

    def test_account_commands(self):
        """Test encoding/decoding of account-related commands"""
        test_cases = [
            # Auth command
            (
                protocol.Command.AUTH,
                b'\x04test\x08password',  # username_len(1) + username(4) + password_len(1) + password(8)
                14
            ),
            # Create account command
            (
                protocol.Command.CREATE_ACCOUNT,
                b'\x07newuser\x08newpass',  # username_len(1) + username(7) + password_len(1) + password(8)
                16
            ),
            # List accounts command
            (
                protocol.Command.LIST_ACCOUNTS,
                b'\x01*',  # pattern_len(1) + pattern(1)
                2
            )
        ]
        
        for command, payload, expected_length in test_cases:
            with self.subTest(command=command):
                # Test encoding
                message = protocol.encode_message(command, payload)
                self.assertEqual(len(message), expected_length + 3)  # +3 for header
                
                # Test decoding
                decoded_command, decoded_payload = protocol.decode_message(message)
                self.assertEqual(decoded_command, command)
                self.assertEqual(decoded_payload, payload)

    def test_message_commands(self):
        """Test encoding/decoding of message-related commands"""
        test_cases = [
            # Send message
            (
                protocol.Command.SEND_MESSAGE,
                b'\x03bob\x00\x0AHello, Bob!',  # recipient_len(1) + recipient(3) + content_len(2) + content(10)
                17
            ),
            # Get messages
            (
                protocol.Command.GET_MESSAGES,
                b'\x00',  # include_read(1)
                1
            ),
            # Mark read
            (
                protocol.Command.MARK_READ,
                b'\x00\x02\x00\x00\x00\x01\x00\x00\x00\x02',  # count(2) + id1(4) + id2(4)
                10
            ),
            # Get unread count
            (
                protocol.Command.GET_UNREAD_COUNT,
                b'',  # Empty payload
                0
            ),
            # Delete messages
            (
                protocol.Command.DELETE_MESSAGES,
                b'\x00\x01\x00\x00\x00\x05',  # count(2) + id(4)
                6
            )
        ]
        
        for command, payload, expected_length in test_cases:
            with self.subTest(command=command):
                # Test encoding
                message = protocol.encode_message(command, payload)
                self.assertEqual(len(message), expected_length + 3)  # +3 for header
                
                # Test decoding
                decoded_command, decoded_payload = protocol.decode_message(message)
                self.assertEqual(decoded_command, command)
                self.assertEqual(decoded_payload, payload)

    def test_message_responses(self):
        """Test message response formats"""
        test_cases = [
            # Send message response
            (
                protocol.Command.SEND_MESSAGE,
                struct.pack('!IQ', 1, int(datetime.now().timestamp())),  # message_id(4) + timestamp(8)
                12
            ),
            # Get messages response (single message)
            (
                protocol.Command.GET_MESSAGES,
                b'\x00\x01'  # count(2) + message data...
                b'\x00\x00\x00\x01'  # id(4)
                b'\x05alice'  # sender_len(1) + sender(5)
                b'\x00\x0AHello, Bob!'  # content_len(2) + content(10)
                b'\x00\x00\x00\x00\x00\x00\x00\x01'  # timestamp(8)
                b'\x00',  # is_read(1)
                34
            ),
            # Mark read response
            (
                protocol.Command.MARK_READ,
                b'\x00\x01',  # count(2)
                2
            ),
            # Get unread count response
            (
                protocol.Command.GET_UNREAD_COUNT,
                b'\x00\x05',  # count(2)
                2
            ),
            # Delete messages response
            (
                protocol.Command.DELETE_MESSAGES,
                b'\x00\x02',  # count(2)
                2
            )
        ]
        
        for command, payload, expected_length in test_cases:
            with self.subTest(command=command):
                message = protocol.encode_message(command, payload)
                self.assertEqual(len(message), expected_length + 3)  # +3 for header
                
                decoded_command, decoded_payload = protocol.decode_message(message)
                self.assertEqual(decoded_command, command)
                self.assertEqual(len(decoded_payload), expected_length)

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

if __name__ == '__main__':
    unittest.main(verbosity=2) 