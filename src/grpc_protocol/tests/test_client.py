"""
Unit tests for the gRPC chat client implementation.
"""

import unittest
import grpc
import grpc_testing
import time
from datetime import datetime

from .. import chat_pb2
from .. import client_grpc
from .. import chat_pb2_grpc

class TestGRPCChatClient(unittest.TestCase):
    """Test cases for GRPCChatClient class"""
    
    def setUp(self):
        """Set up test environment before each test"""
        self._real_time = grpc_testing.strict_real_time()
        self._fake_time = grpc_testing.fake_time(time.time())
        
        self.service_descriptors = chat_pb2.DESCRIPTOR.services_by_name['ChatService']
        self.test_server = grpc_testing.server_from_dictionary(
            {
                self.service_descriptors: chat_pb2_grpc.ChatServiceServicer()
            },
            self._fake_time
        )
        
        # Create client with mock channel
        self.client = client_grpc.GRPCChatClient()
        self.client.channel = self.test_server
        self.client.stub = chat_pb2_grpc.ChatServiceStub(self.client.channel)

    def test_create_account_success(self):
        """Test successful account creation"""
        # Prepare mock response
        expected_response = chat_pb2.CreateAccountResponse(
            success=True,
            error_message=""
        )
        
        # Set up mock behavior
        invoke_future = self.test_server.invoke_unary_unary(
            self.service_descriptors.methods_by_name['CreateAccount'],
            (),
            expected_response,
            None
        )
        
        # Test the client method
        success, error = self.client.create_account("testuser", "password123")
        
        # Verify results
        self.assertTrue(success)
        self.assertEqual(error, "")

    def test_create_account_failure(self):
        """Test account creation with existing username"""
        # Prepare mock response
        expected_response = chat_pb2.CreateAccountResponse(
            success=False,
            error_message="Username already exists"
        )
        
        # Set up mock behavior
        invoke_future = self.test_server.invoke_unary_unary(
            self.service_descriptors.methods_by_name['CreateAccount'],
            (),
            expected_response,
            None
        )
        
        # Test the client method
        success, error = self.client.create_account("existinguser", "password123")
        
        # Verify results
        self.assertFalse(success)
        self.assertEqual(error, "Username already exists")

    def test_login_success(self):
        """Test successful login"""
        # Prepare mock response
        expected_response = chat_pb2.AuthResponse(
            success=True,
            error_message=""
        )
        
        # Set up mock behavior
        invoke_future = self.test_server.invoke_unary_unary(
            self.service_descriptors.methods_by_name['Authenticate'],
            (),
            expected_response,
            None
        )
        
        # Test the client method
        success, error = self.client.login("testuser", "password123")
        
        # Verify results
        self.assertTrue(success)
        self.assertEqual(error, "")
        self.assertEqual(self.client.current_user, "testuser")

    def test_send_message_success(self):
        """Test sending a message successfully"""
        # Set up authenticated state
        self.client.current_user = "sender"
        
        # Prepare mock response
        expected_response = chat_pb2.SendMessageResponse(
            message_id=123,
            error_message=""
        )
        
        # Set up mock behavior
        invoke_future = self.test_server.invoke_unary_unary(
            self.service_descriptors.methods_by_name['SendMessage'],
            (),
            expected_response,
            None
        )
        
        # Test the client method
        msg_id, error = self.client.send_message("recipient", "Hello!")
        
        # Verify results
        self.assertEqual(msg_id, 123)
        self.assertEqual(error, "")

    def test_get_messages_success(self):
        """Test retrieving messages successfully"""
        # Set up authenticated state
        self.client.current_user = "testuser"
        
        # Create mock message
        test_message = chat_pb2.Message(
            id=1,
            sender="friend",
            content="Hello!",
            timestamp=int(time.time()),
            is_read=False
        )
        
        # Prepare mock response
        expected_response = chat_pb2.GetMessagesResponse(
            messages=[test_message],
            error_message=""
        )
        
        # Set up mock behavior
        invoke_future = self.test_server.invoke_unary_unary(
            self.service_descriptors.methods_by_name['GetMessages'],
            (),
            expected_response,
            None
        )
        
        # Test the client method
        messages, error = self.client.get_messages()
        
        # Verify results
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['sender'], "friend")
        self.assertEqual(messages[0]['content'], "Hello!")
        self.assertEqual(error, "")

if __name__ == '__main__':
    unittest.main() 