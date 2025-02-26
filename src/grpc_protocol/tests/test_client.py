"""
Unit tests for the gRPC chat client implementation.
"""

import unittest
import grpc
import time
from unittest.mock import MagicMock, patch, Mock
from .. import chat_pb2
from .. import client
import logging

class TestGRPCChatClient(unittest.TestCase):
    """Unit tests for gRPC chat client"""
    
    def setUp(self):
        """Set up test client with mocked stub"""
        # Create a mock stub
        self.mock_stub = Mock()
        
        # Create client and replace its stub with our mock
        self.client = client.GRPCChatClient(host='localhost', port=50051)
        self.client.stub = self.mock_stub
        
        logging.info("Set up test client with mock stub")

    def test_create_account_success(self):
        """Test successful account creation"""
        # Set up mock response
        username = "testuser"
        password = "password123"
        mock_response = chat_pb2.CreateAccountResponse(
            success=True,
            error_message=""
        )
        expected_request = chat_pb2.CreateAccountRequest(
            username=username, 
            password_hash=self.client._hash_password(password)
        )
        
        self.client.stub.CreateAccount.return_value = mock_response
        
        # Test the client method
        success, error = self.client.create_account(username, password)

        # Verify results
        self.client.stub.CreateAccount.assert_called_once_with(expected_request)
        self.assertTrue(success)
        self.assertEqual(error, "")

    def test_create_account_failure(self):
        """Test account creation with existing username"""
        # Set up mock response
        username = "existinguser"
        password = "password123"

        mock_response = chat_pb2.CreateAccountResponse(
            success=False,
            error_message="Username already exists"
        )
        expected_request = chat_pb2.CreateAccountRequest(
            username=username, 
            password_hash=self.client._hash_password(password)
        )

        self.client.stub.CreateAccount.return_value = mock_response
        
        # Test the client method
        success, error = self.client.create_account(username, password)
        
        # Verify results
        self.client.stub.CreateAccount.assert_called_once_with(expected_request)
        self.assertFalse(success)
        self.assertEqual(error, "Username already exists")

    def test_login_success(self):
        """Test successful login"""
        # Mock successful response
        username = "testuser"
        password = "password123"
        expected_request = chat_pb2.AuthRequest(
            username=username,
            password_hash=self.client._hash_password(password)
        )
        self.mock_stub.Authenticate.return_value = chat_pb2.AuthResponse(
            success=True,
            error_message=""
        )
        
        success = self.client.login(username, password)
        
        self.assertTrue(success)
        self.assertEqual(self.client.current_user, "testuser")
        self.mock_stub.Authenticate.assert_called_once_with(expected_request)

    def test_login_failure(self):
        """Test login with incorrect credentials"""
        # Mock failed response
        username = "testuser"
        password = "wrongpassword"
        expected_request = chat_pb2.AuthRequest(
            username=username,
            password_hash=self.client._hash_password(password)
        )
        self.mock_stub.Authenticate.return_value = chat_pb2.AuthResponse(
            success=False,
            error_message="Invalid username or password"
        )
        
        success = self.client.login(username, password)
        
        self.assertFalse(success)
        self.assertIsNone(self.client.current_user)
        self.mock_stub.Authenticate.assert_called_once_with(expected_request)

    def test_send_message_success(self):
        """Test sending a message successfully"""
        # Set up authenticated state
        username = "sender"
        self.client.current_user = username
        metadata = [('username', username)]

        
        # Set up mock response
        recipient = "recipient"
        content = "Hello!"
        expected_request = chat_pb2.SendMessageRequest(
            recipient=recipient,
            content=content
        )
        mock_response = chat_pb2.SendMessageResponse(
            message_id=123,
            error_message=""
        )
        self.client.stub.SendMessage.return_value = mock_response
        
        # Test the client method
        msg_id, error = self.client.send_message(recipient, content)
        
        # Verify results
        self.assertEqual(msg_id, 123)
        self.assertEqual(error, "")
        self.client.stub.SendMessage.assert_called_once_with(expected_request, metadata=metadata)

    def test_send_message_not_authenticated(self):
        """Test sending message without being logged in"""
        # Ensure no user is authenticated
        self.client.current_user = None
        
        # Test the client method
        msg_id, error = self.client.send_message("recipient", "Hello!")
        
        # Verify results
        self.assertEqual(msg_id, 0)
        self.assertEqual(error, "Not authenticated")
        
        # Verify the stub was never called
        self.client.stub.SendMessage.assert_not_called()

    def test_get_messages_success(self):
        """Test retrieving messages successfully"""
        username = "testuser"
        self.client.current_user = username
        metadata = [('username', username)]
        expected_request = chat_pb2.GetMessagesRequest(include_read = True)
        self.mock_stub.GetMessages.return_value = chat_pb2.GetMessagesResponse(
            messages=[
                chat_pb2.Message(
                    id=1,
                    sender="user1",
                    recipient=username,
                    content="Hello",
                    timestamp=123456789,
                    is_read=False
                ),
                chat_pb2.Message(
                    id=4,
                    sender="user2",
                    recipient=username,
                    content="Hello2",
                    timestamp=123456790,
                    is_read=True
                )
            ],
            error_message=""
        )
        
        messages = self.client.get_messages()
        
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]['content'], "Hello")
        self.assertEqual(messages[1]['id'], 4)
        self.mock_stub.GetMessages.assert_called_once_with(expected_request, metadata = metadata)

    def test_get_messages_empty_response(self):
        """Test getting messages when there are none"""
        username = "testuser"
        self.client.current_user = username
        metadata = [('username', username)]
        expected_request = chat_pb2.GetMessagesRequest(include_read = True)
        self.mock_stub.GetMessages.return_value = chat_pb2.GetMessagesResponse(
            messages=[],
            error_message=""
        )
        
        messages = self.client.get_messages()
        
        self.assertEqual(messages, [])
        self.mock_stub.GetMessages.assert_called_once_with(expected_request, metadata=metadata)

    def test_get_messages_network_error(self):
        """Test handling of network errors during message retrieval"""
        self.client.current_user = "testuser"
        self.mock_stub.GetMessages.side_effect = grpc.RpcError("Network error")
        
        messages = self.client.get_messages()
        self.assertEqual(messages, [])

    def test_create_account_network_error(self):
        """Test handling of network errors during account creation"""
        # Set up mock to raise gRPC error
        self.client.stub.CreateAccount.side_effect = grpc.RpcError("Network error")
        
        # Test the client method
        success, error = self.client.create_account("testuser", "password123")
        
        # Verify results
        self.assertFalse(success)
        self.assertEqual(error, "Network error")

    def test_send_message_with_empty_content(self):
        """Test sending a message with empty content"""
        # Set up authenticated state
        self.client.current_user = "sender"
        
        # Test the client method
        msg_id, error = self.client.send_message("recipient", "")
        
        # Verify results
        self.assertEqual(msg_id, 0)
        self.assertEqual(error, "Message content cannot be empty")
        
        # Verify the stub was never called
        self.client.stub.SendMessage.assert_not_called()

    def test_send_message_with_empty_recipient(self):
        """Test sending a message with empty recipient"""
        # Set up authenticated state
        self.client.current_user = "sender"
        
        # Test the client method
        msg_id, error = self.client.send_message("", "Hello!")
        
        # Verify results
        self.assertEqual(msg_id, 0)
        self.assertEqual(error, "Recipient cannot be empty")
        
        # Verify the stub was never called
        self.client.stub.SendMessage.assert_not_called()

    def test_connect_success(self):
        """Test successful connection to server"""
        # Mock the channel creation
        with patch('grpc.insecure_channel') as mock_channel:
            # Configure the mock
            mock_channel.return_value = MagicMock()
            
            # Test the connect method
            success = self.client.connect()
            
            # Verify results
            self.assertTrue(success)
            mock_channel.assert_called_once_with(f'{self.client.host}:{self.client.port}')

    def test_connect_failure(self):
        """Test failed connection to server"""
        print("\nNote: The following error log is expected as part of testing error handling:")
        # Mock the channel creation to raise an error
        with patch('grpc.insecure_channel') as mock_channel:
            mock_channel.side_effect = Exception("Connection failed")
            
            # Test the connect method
            success = self.client.connect()
            
            # Verify results
            self.assertFalse(success)

    def test_connect_failure_logs_error(self):
        """Test that connection failure is properly logged"""
        print("\nNote: The following error log is expected as part of testing error handling:")
        # Mock both the channel creation and logging
        with patch('grpc.insecure_channel') as mock_channel, \
             patch('logging.error') as mock_log:
            # Setup the channel to fail
            mock_channel.side_effect = Exception("Connection failed")
            
            # Test the connect method
            success = self.client.connect()
            
            # Verify results
            self.assertFalse(success)
            mock_log.assert_called_once_with("Failed to connect: Connection failed")

    def test_disconnect(self):
        """Test disconnecting from server"""
        # Create a mock channel
        mock_channel = MagicMock()
        self.client.channel = mock_channel
        
        # Test the disconnect method
        self.client.disconnect()
        
        # Verify the channel was closed
        mock_channel.close.assert_called_once()

    def test_get_messages_with_read_filter(self):
        """Test getting only unread messages"""
        self.client.current_user = "testuser"
        self.client.stub.GetMessages.return_value = chat_pb2.GetMessagesResponse(
            messages=[
                chat_pb2.Message(id=1, is_read=True),
                chat_pb2.Message(id=2, is_read=False)
            ]
        )
        
        # Returns filtered list
        messages = self.client.get_messages(include_read=False)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['id'], 2)

    def test_mark_read_success(self):
        """Test marking messages as read successfully"""
        # Set up authenticated state
        self.client.current_user = "testuser"
        metadata = [('username', "testuser")]
        
        # Set up mock response
        message_ids = [1, 2, 3]
        expected_request = chat_pb2.MarkReadRequest(
            message_ids=message_ids
        )
        mock_response = chat_pb2.MarkReadResponse(
            success=True,
            error_message=""
        )
        self.client.stub.MarkRead.return_value = mock_response
        
        # Test the client method
        success, error = self.client.mark_read(message_ids)
        
        # Verify results
        self.assertTrue(success)
        self.assertEqual(error, "")
        self.client.stub.MarkRead.assert_called_once_with(expected_request, metadata=metadata)

    def test_mark_read_not_authenticated(self):
        """Test marking messages as read without being logged in"""
        self.client.current_user = None
        
        success, error = self.client.mark_read([1, 2, 3])
        
        self.assertFalse(success)
        self.assertEqual(error, "Not authenticated")
        self.client.stub.MarkRead.assert_not_called()

    def test_delete_messages_success(self):
        """Test deleting messages successfully"""
        # Set up authenticated state
        self.client.current_user = "testuser"
        metadata = [('username', "testuser")]
        
        # Set up mock response
        message_ids = [1, 2, 3]
        expected_request = chat_pb2.DeleteMessagesRequest(
            message_ids=message_ids
        )
        mock_response = chat_pb2.DeleteMessagesResponse(
            success=True,
            error_message=""
        )
        self.client.stub.DeleteMessages.return_value = mock_response
        
        # Test the client method
        success, error = self.client.delete_messages(message_ids)
        
        # Verify results
        self.assertTrue(success)
        self.assertEqual(error, "")
        self.client.stub.DeleteMessages.assert_called_once_with(expected_request, metadata=metadata)

    def test_delete_messages_not_authenticated(self):
        """Test deleting messages without being logged in"""
        self.client.current_user = None
        
        success, error = self.client.delete_messages([1, 2, 3])
        
        self.assertFalse(success)
        self.assertEqual(error, "Not authenticated")
        self.client.stub.DeleteMessages.assert_not_called()

    def test_list_accounts_success(self):
        """Test listing accounts successfully"""
        # Set up authenticated state
        self.client.current_user = "testuser"
        metadata = [('username', "testuser")]
        
        # Set up mock response
        expected_request = chat_pb2.ListAccountsRequest(pattern="*")
        mock_response = chat_pb2.ListAccountsResponse(
            usernames=["user1", "user2", "user3"]
        )
        self.client.stub.ListAccounts.return_value = mock_response
        
        # Test the client method
        usernames = self.client.list_accounts()
        
        # Verify results
        self.assertEqual(usernames, ["user1", "user2", "user3"])
        self.client.stub.ListAccounts.assert_called_once_with(expected_request, metadata=metadata)

    def test_list_accounts_with_pattern(self):
        """Test listing accounts with a specific pattern"""
        self.client.current_user = "testuser"
        metadata = [('username', "testuser")]
        
        expected_request = chat_pb2.ListAccountsRequest(pattern="test*")
        mock_response = chat_pb2.ListAccountsResponse(
            usernames=["testuser1", "testuser2"]
        )
        self.client.stub.ListAccounts.return_value = mock_response
        
        usernames = self.client.list_accounts("test*")
        
        self.assertEqual(usernames, ["testuser1", "testuser2"])
        self.client.stub.ListAccounts.assert_called_once_with(expected_request, metadata=metadata)

    def test_delete_account_success(self):
        """Test deleting account successfully"""
        # Set up authenticated state
        username = "testuser"
        password = "password123"
        self.client.current_user = username
        metadata = [('username', username)]
        
        # Set up mock response
        expected_request = chat_pb2.DeleteAccountRequest(
            username=username,
            password_hash=self.client._hash_password(password)
        )
        mock_response = chat_pb2.DeleteAccountResponse(
            success=True,
            error_message=""
        )
        self.client.stub.DeleteAccount.return_value = mock_response
        
        # Test the client method
        success = self.client.delete_account(username, password)
        
        # Verify results
        self.assertTrue(success)
        self.assertIsNone(self.client.current_user)  # Should clear current user
        self.client.stub.DeleteAccount.assert_called_once_with(expected_request, metadata=metadata)

    def test_delete_account_other_user(self):
        """Test deleting another user's account"""
        # Set up authenticated state as admin
        self.client.current_user = "admin"
        metadata = [('username', "admin")]
        
        # Set up mock response
        username = "testuser"
        password = "password123"
        expected_request = chat_pb2.DeleteAccountRequest(
            username=username,
            password_hash=self.client._hash_password(password)
        )
        mock_response = chat_pb2.DeleteAccountResponse(
            success=True,
            error_message=""
        )
        self.client.stub.DeleteAccount.return_value = mock_response
        
        # Test the client method
        success = self.client.delete_account(username, password)
        
        # Verify results
        self.assertTrue(success)
        self.assertEqual(self.client.current_user, "admin")  # Should not clear current user
        self.client.stub.DeleteAccount.assert_called_once_with(expected_request, metadata=metadata)

    def test_delete_account_failure(self):
        """Test deleting account with incorrect credentials"""
        username = "testuser"
        password = "wrongpassword"
        self.client.current_user = username
        metadata = [('username', username)]
        
        expected_request = chat_pb2.DeleteAccountRequest(
            username=username,
            password_hash=self.client._hash_password(password)
        )
        mock_response = chat_pb2.DeleteAccountResponse(
            success=False,
            error_message="Invalid credentials"
        )
        self.client.stub.DeleteAccount.return_value = mock_response
        
        success = self.client.delete_account(username, password)
        
        self.assertFalse(success)
        self.assertEqual(self.client.current_user, username)  # Should not clear current user
        self.client.stub.DeleteAccount.assert_called_once_with(expected_request, metadata=metadata)

if __name__ == '__main__':
    unittest.main() 