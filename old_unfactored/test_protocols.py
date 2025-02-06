"""
Protocol Comparison Tests

This module compares the custom binary protocol with the JSON protocol
in terms of message size and encoding/decoding performance.
"""

import unittest
import time
from typing import Dict, Any, Tuple
from src.custom_protocol import protocol
from src.json_protocol import protocol as json_protocol

class ProtocolComparisonTests(unittest.TestCase):
    """Test cases comparing custom and JSON protocols"""

    def setUp(self):
        """Set up test data""" #DEFINE HERE SOME TEST CASES OF MESSAGES TO BE SENT. WRITTEN IN JSON FORMAT.
        self.test_cases = {
            "AUTH": {
                "username": "testuser123",
                "password_hash": "a" * 32  # Simulate a 32-byte hash
            },
            "SEND_MESSAGE": {
                "recipient": "user456",
                "message": "Hello, this is a test message that's relatively long to simulate real-world usage!",
                "timestamp": "2024-02-01T12:34:56Z"
            },
            "LIST_ACCOUNTS": {
                "pattern": "test*",
                "page": 1,
                "page_size": 20
            }
        }

    def json_to_custom_payload(self, msg_type: str, payload: Dict[str, Any]) -> Tuple[protocol.Command, bytes]:
        """
        Convert a JSON payload to the custom protocol format.
        
        Args:
            msg_type: The type of message (AUTH, SEND_MESSAGE, etc.)
            payload: The JSON payload dictionary
            
        Returns:
            Tuple containing the custom protocol command and encoded payload
        """
        if msg_type == "AUTH":
            custom_payload = (
                bytes([len(payload["username"])]) +
                payload["username"].encode() +
                payload["password_hash"].encode()
            )
            return protocol.Command.AUTH, custom_payload
            
        elif msg_type == "SEND_MESSAGE":
            custom_payload = (
                bytes([len(payload["recipient"])]) +
                payload["recipient"].encode() +
                len(payload["message"]).to_bytes(2, 'big') +
                payload["message"].encode()
            )
            return protocol.Command.SEND_MESSAGE, custom_payload
            
        else:  # LIST_ACCOUNTS and other messages
            custom_payload = str(payload).encode()
            return protocol.Command.LIST_ACCOUNTS, custom_payload

    def test_message_sizes(self):
        """Compare message sizes between protocols"""
        print("\nMessage Size Comparison:")
        print("-" * 60)
        print(f"{'Message Type':<20} {'Custom (bytes)':<15} {'JSON (bytes)':<15} {'Ratio':<10}")
        print("-" * 60)

        for msg_type, payload in self.test_cases.items():
            # Custom protocol
            command, custom_payload = self.json_to_custom_payload(msg_type, payload)
            custom_msg = protocol.encode_message(command, custom_payload)

            # JSON protocol
            json_msg = json_protocol.encode_message(
                getattr(json_protocol.Command, msg_type),
                payload
            ) # Getting the json string encoded in utf-8

            # Compare sizes
            custom_size = len(custom_msg)
            json_size = len(json_msg) # checking the length of the json string
            ratio = json_size / custom_size

            print(f"{msg_type:<20} {custom_size:<15} {json_size:<15} {ratio:.2f}x")

    def test_encoding_performance(self):
        """Compare encoding performance between protocols"""
        iterations = 10000
        print("\nEncoding Performance Test (10,000 iterations):")
        print("-" * 60)

        for msg_type, payload in self.test_cases.items():
            # Time custom protocol
            command, custom_payload = self.json_to_custom_payload(msg_type, payload)
            
            start_time = time.time()
            for _ in range(iterations):
                protocol.encode_message(command, custom_payload)
            custom_time = time.time() - start_time

            # Time JSON protocol
            start_time = time.time()
            for _ in range(iterations):
                json_protocol.encode_message(
                    getattr(json_protocol.Command, msg_type),
                    payload
                )
            json_time = time.time() - start_time

            print(f"{msg_type}:")
            print(f"  Custom: {custom_time:.4f} seconds")
            print(f"  JSON:   {json_time:.4f} seconds")
            print(f"  Ratio:  {json_time/custom_time:.2f}x slower")

if __name__ == '__main__':
    unittest.main(verbosity=2) 