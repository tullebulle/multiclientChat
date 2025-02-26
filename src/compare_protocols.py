"""
Protocol Comparison Tests

This module compares the custom binary protocol, JSON protocol, and gRPC protocol
in terms of message size and encoding/decoding performance.
"""

import unittest
import time
from typing import Dict, Any, Tuple
from custom_protocol import protocol
from json_protocol import protocol as json_protocol
from grpc_protocol import chat_pb2

class ProtocolComparisonTests(unittest.TestCase):
    """Test cases comparing custom, JSON, and gRPC protocols"""

    def setUp(self):
        """Set up test data"""
        self.test_cases = {
            "AUTH": {
                "username": "testuser123",
                "password_hash": "a" * 32  # Simulate a 32-byte hash
            },
            "SEND_MESSAGE": {
                "recipient": "user456",
                "message": "Hello, this is a test message that's relatively long to simulate real-world usage!",
            },
            "LIST_ACCOUNTS": {
                "pattern": "test*",
            },
            "DELETE_MESSAGES": {
                "message_ids": [2147483630,2147483630,2147483630,2147483630,2147483630,2147483630]#[1,4,12,8,2025,100_000_000]
            }
        }

    def json_to_custom_payload(self, msg_type: str, payload: Dict[str, Any]) -> Tuple[protocol.Command, bytes]:
        """Convert a JSON payload to the custom protocol format"""
        if msg_type == "AUTH":
            custom_payload = (
                len(payload["username"]).to_bytes(1, 'big') +
                payload["username"].encode() +
                len(payload["password_hash"]).to_bytes(1, 'big') +
                payload["password_hash"].encode()
            )
            return protocol.Command.AUTH, custom_payload
            
        elif msg_type == "SEND_MESSAGE":
            custom_payload = (
                len(payload["recipient"]).to_bytes(1, 'big') +
                payload["recipient"].encode() +
                len(payload["message"]).to_bytes(2, 'big') +
                payload["message"].encode()
            )
            return protocol.Command.SEND_MESSAGE, custom_payload
            
        elif msg_type == "LIST_ACCOUNTS":
            custom_payload = (
                len(payload["pattern"]).to_bytes(1, 'big') +
                payload["pattern"].encode() 
            )
            return protocol.Command.LIST_ACCOUNTS, custom_payload
        
        elif msg_type == "DELETE_MESSAGES":
            msg_ids_payload = bytes()
            for id in payload["message_ids"]:
                msg_ids_payload += id.to_bytes(4, 'big')
            custom_payload = (
                len(payload["message_ids"]).to_bytes(2, 'big') +
                msg_ids_payload
            )
            return protocol.Command.DELETE_MESSAGES, custom_payload

    def json_to_grpc_message(self, msg_type: str, payload: Dict[str, Any]) -> Any:
        """Convert a JSON payload to the corresponding gRPC message"""
        if msg_type == "AUTH":
            return chat_pb2.AuthRequest(
                username=payload["username"],
                password_hash=payload["password_hash"]
            )
        elif msg_type == "SEND_MESSAGE":
            return chat_pb2.SendMessageRequest(
                recipient=payload["recipient"],
                content=payload["message"]
            )
        elif msg_type =="LIST_ACCOUNTS":
            return chat_pb2.ListAccountsRequest(
                pattern=payload["pattern"]
            )
        elif msg_type =="DELETE_MESSAGES":
            return chat_pb2.DeleteMessagesRequest(
                message_ids = payload["message_ids"]
            )

    def test_message_sizes(self):
        """Compare message sizes between protocols"""
        print("\nMessage Size Comparison:")
        print("-" * 80)
        print(f"{'Message Type':<15} {'Custom (bytes)':<15} {'JSON (bytes)':<15} {'gRPC (bytes)':<15} {'JSON/Custom':<12} {'gRPC/Custom':<12}")
        print("-" * 80)

        for msg_type, payload in self.test_cases.items():
            # Custom protocol
            command, custom_payload = self.json_to_custom_payload(msg_type, payload)
            custom_msg = protocol.encode_message(command, custom_payload)
            custom_size = len(custom_msg)

            # JSON protocol
            json_msg = json_protocol.encode_message(
                getattr(json_protocol.Command, msg_type),
                payload
            )
            json_size = len(json_msg)

            # gRPC protocol
            grpc_msg = self.json_to_grpc_message(msg_type, payload)
            grpc_size = grpc_msg.ByteSize()

            # Calculate ratios
            json_ratio = json_size / custom_size
            grpc_ratio = grpc_size / custom_size

            print(f"{msg_type:<15} {custom_size:<15} {json_size:<15} {grpc_size:<15} {json_ratio:.2f}x{' ':6} {grpc_ratio:.2f}x")

    def test_encoding_performance(self):
        """Compare encoding performance between protocols"""
        iterations = 10000
        print("\nEncoding Performance Test (10,000 iterations):")
        print("-" * 60)

        for msg_type, payload in self.test_cases.items():
            print(f"\n{msg_type}:")
            
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

            # Time gRPC protocol
            grpc_msg = self.json_to_grpc_message(msg_type, payload)
            start_time = time.time()
            for _ in range(iterations):
                grpc_msg.SerializeToString()
            grpc_time = time.time() - start_time

            print(f"  Custom: {custom_time:.4f} seconds")
            print(f"  JSON:   {json_time:.4f} seconds ({json_time/custom_time:.2f}x slower)")
            print(f"  gRPC:   {grpc_time:.4f} seconds ({grpc_time/custom_time:.2f}x slower)")

if __name__ == '__main__':
    unittest.main(verbosity=2) 