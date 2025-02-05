"""
JSON Protocol Unit Tests

Tests the JSON protocol message encoding and decoding.
"""

import unittest
from datetime import datetime
from .. import protocol
import json

class TestJSONProtocol(unittest.TestCase):
    """Unit tests for JSON protocol implementation"""

    def test_account_commands(self):
        """Test encoding/decoding of account-related commands"""
        test_cases = [
            # Auth command
            (
                protocol.Command.AUTH,
                {
                    "username": "testuser",
                    "password_hash": "hashedpass"
                },
                {
                    "command": "AUTH",
                    "payload": {
                        "username": "testuser",
                        "password_hash": "hashedpass"
                    }
                }
            ),
            # Create account command
            (
                protocol.Command.CREATE_ACCOUNT,
                {
                    "username": "newuser",
                    "password": "newpass"
                },
                {
                    "command": "CREATE_ACCOUNT",
                    "payload": {
                        "username": "newuser",
                        "password": "newpass"
                    }
                }
            ),
            # List accounts command
            (
                protocol.Command.LIST_ACCOUNTS,
                {
                    "pattern": "*",
                    "page": 1,
                    "page_size": 10
                },
                {
                    "command": "LIST_ACCOUNTS",
                    "payload": {
                        "pattern": "*",
                        "page": 1,
                        "page_size": 10
                    }
                }
            )
        ]
        
        for command, payload, expected in test_cases:
            with self.subTest(command=command):
                # Test encoding
                encoded = protocol.encode_message(command, payload)
                decoded_json = json.loads(encoded.decode('utf-8'))
                self.assertEqual(decoded_json, expected)
                
                # Test decoding
                cmd, pl = protocol.decode_message(encoded)
                self.assertEqual(cmd, command.name)
                self.assertEqual(pl, payload)

    def test_message_commands(self):
        """Test encoding/decoding of message-related commands"""
        test_cases = [
            # Send message
            (
                protocol.Command.SEND_MESSAGE,
                {
                    "recipient": "bob",
                    "content": "Hello, Bob!"
                },
                {
                    "command": "SEND_MESSAGE",
                    "payload": {
                        "recipient": "bob",
                        "content": "Hello, Bob!"
                    }
                }
            ),
            # Get messages
            (
                protocol.Command.GET_MESSAGES,
                {
                    "include_read": False
                },
                {
                    "command": "GET_MESSAGES",
                    "payload": {
                        "include_read": False
                    }
                }
            ),
            # Mark messages as read
            (
                protocol.Command.MARK_READ,
                {
                    "message_ids": [1, 2, 3]
                },
                {
                    "command": "MARK_READ",
                    "payload": {
                        "message_ids": [1, 2, 3]
                    }
                }
            ),
            # Get unread count
            (
                protocol.Command.GET_UNREAD_COUNT,
                {},
                {
                    "command": "GET_UNREAD_COUNT",
                    "payload": {}
                }
            ),
            # Delete messages
            (
                protocol.Command.DELETE_MESSAGES,
                {
                    "message_ids": [4, 5, 6]
                },
                {
                    "command": "DELETE_MESSAGES",
                    "payload": {
                        "message_ids": [4, 5, 6]
                    }
                }
            )
        ]
        
        for command, payload, expected in test_cases:
            with self.subTest(command=command):
                # Test encoding
                encoded = protocol.encode_message(command, payload)
                decoded_json = json.loads(encoded.decode('utf-8'))
                self.assertEqual(decoded_json, expected)
                
                # Test decoding
                cmd, pl = protocol.decode_message(encoded)
                self.assertEqual(cmd, command.name)
                self.assertEqual(pl, payload)

    def test_special_content(self):
        """Test handling of special characters in message content"""
        test_cases = [
            "Hello, World! 👋",
            "Multi\nline\nmessage",
            "Special chars: ™€¢",
            "Unicode: 你好, Привет, مرحبا",
            "Quotes: 'single' and \"double\"",
            "Symbols: @#$%^&*()",
        ]
        
        for content in test_cases:
            with self.subTest(content=content):
                payload = {
                    "recipient": "bob",
                    "content": content
                }
                encoded = protocol.encode_message(
                    protocol.Command.SEND_MESSAGE,
                    payload
                )
                _, decoded_payload = protocol.decode_message(encoded)
                self.assertEqual(decoded_payload["content"], content)

    def test_large_messages(self):
        """Test handling of large messages"""
        large_content = "x" * 1000  # 1KB message
        payload = {
            "recipient": "bob",
            "content": large_content
        }
        
        encoded = protocol.encode_message(
            protocol.Command.SEND_MESSAGE,
            payload
        )
        _, decoded_payload = protocol.decode_message(encoded)
        self.assertEqual(decoded_payload["content"], large_content)

    def test_error_responses(self):
        """Test error response formatting"""
        error_cases = [
            ("Not authenticated", "Authentication required"),
            ("Invalid recipient", "User does not exist"),
            ("Permission denied", "Cannot access these messages"),
        ]
        
        for error_type, message in error_cases:
            with self.subTest(error_type=error_type):
                payload = {
                    "status": "error",
                    "error_type": error_type,
                    "message": message
                }
                encoded = protocol.encode_message(
                    protocol.Command.ERROR,
                    payload
                )
                _, decoded_payload = protocol.decode_message(encoded)
                self.assertEqual(decoded_payload["status"], "error")
                self.assertEqual(decoded_payload["message"], message)

if __name__ == '__main__':
    unittest.main(verbosity=2) 