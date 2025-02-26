"""
Unit tests for the gRPC chat server implementation.
"""

import unittest
import grpc
from unittest.mock import MagicMock, patch, Mock
from .. import chat_pb2
from .. import server
import logging
import threading

class TestChatServicer(unittest.TestCase):
    """Unit tests for ChatServicer"""
    
    def setUp(self):
        """Set up test server"""
        self.servicer = server.ChatServicer()
        self.context = MagicMock()
        logging.info("Set up test servicer")

    def test_create_account_success(self):
        """Test successful account creation"""
        request = chat_pb2.CreateAccountRequest(
            username="testuser",
            password_hash="hashed_password"
        )
        
        response = self.servicer.CreateAccount(request, self.context)
        
        self.assertTrue(response.success)
        self.assertEqual(response.error_message, "")
        self.assertIn("testuser", self.servicer.accounts)
        self.assertEqual(self.servicer.accounts["testuser"], "hashed_password")

    def test_create_account_duplicate(self):
        """Test account creation with existing username"""
        # Create first account
        request1 = chat_pb2.CreateAccountRequest(
            username="testuser",
            password_hash="hashed_password1"
        )
        self.servicer.CreateAccount(request1, self.context)
        
        # Try to create duplicate account
        request2 = chat_pb2.CreateAccountRequest(
            username="testuser",
            password_hash="hashed_password2"
        )
        response = self.servicer.CreateAccount(request2, self.context)
        
        self.assertFalse(response.success)
        self.assertEqual(response.error_message, "Username already exists")
        self.assertEqual(self.servicer.accounts["testuser"], "hashed_password1")

    def test_authenticate_success(self):
        """Test successful authentication"""
        # Create account first
        self.servicer.accounts["testuser"] = "hashed_password"
        
        request = chat_pb2.AuthRequest(
            username="testuser",
            password_hash="hashed_password"
        )
        
        response = self.servicer.Authenticate(request, self.context)
        
        self.assertTrue(response.success)
        self.assertEqual(response.error_message, "")

    def test_authenticate_failure_wrong_password(self):
        """Test authentication with wrong password"""
        self.servicer.accounts["testuser"] = "hashed_password"
        
        request = chat_pb2.AuthRequest(
            username="testuser",
            password_hash="wrong_password"
        )
        
        response = self.servicer.Authenticate(request, self.context)
        
        self.assertFalse(response.success)
        self.assertEqual(response.error_message, "Invalid username or password")

    def test_send_message_success(self):
        """Test successful message sending"""
        # Setup accounts
        self.servicer.accounts["sender"] = "pass1"
        self.servicer.accounts["recipient"] = "pass2"
        
        # Mock authentication context
        self.context.invocation_metadata.return_value = [('username', 'sender')]
        
        request = chat_pb2.SendMessageRequest(
            recipient="recipient",
            content="Hello!"
        )
        
        response = self.servicer.SendMessage(request, self.context)
        
        self.assertNotEqual(response.message_id, 0)
        self.assertEqual(response.error_message, "")
        self.assertEqual(len(self.servicer.messages), 1)
        self.assertEqual(self.servicer.messages[0].sender, "sender")
        self.assertEqual(self.servicer.messages[0].recipient, "recipient")
        self.assertEqual(self.servicer.messages[0].content, "Hello!")

    def test_send_message_not_authenticated(self):
        """Test sending message without authentication"""
        self.context.invocation_metadata.return_value = []
        
        request = chat_pb2.SendMessageRequest(
            recipient="recipient",
            content="Hello!"
        )
        
        response = self.servicer.SendMessage(request, self.context)
        
        self.assertEqual(response.message_id, 0)
        self.assertEqual(response.error_message, "Not authenticated")
        self.assertEqual(len(self.servicer.messages), 0)

    def test_get_messages_success(self):
        """Test getting messages successfully"""
        # Setup test messages
        self.context.invocation_metadata.return_value = [('username', 'recipient')]
        msg = chat_pb2.Message(
            id=1,
            sender="sender",
            recipient="recipient",
            content="Hello!",
            timestamp=123456789,
            is_read=False
        )
        self.servicer.messages.append(msg)
        
        request = chat_pb2.GetMessagesRequest(include_read=True)
        
        response = self.servicer.GetMessages(request, self.context)
        
        self.assertEqual(len(response.messages), 1)
        self.assertEqual(response.messages[0].content, "Hello!")
        self.assertEqual(response.error_message, "")

    def test_mark_read_success(self):
        """Test marking messages as read"""
        # Setup test message
        self.context.invocation_metadata.return_value = [('username', 'recipient')]
        msg = chat_pb2.Message(
            id=1,
            sender="sender",
            recipient="recipient",
            content="Hello!",
            is_read=False
        )
        self.servicer.messages.append(msg)
        
        request = chat_pb2.MarkReadRequest(message_ids=[1])
        
        response = self.servicer.MarkRead(request, self.context)
        
        self.assertTrue(response.success)
        self.assertEqual(response.error_message, "")
        self.assertTrue(self.servicer.messages[0].is_read)

    def test_delete_messages_success(self):
        """Test deleting messages successfully"""
        # Setup test message
        self.context.invocation_metadata.return_value = [('username', 'recipient')]
        msg = chat_pb2.Message(
            id=1,
            sender="sender",
            recipient="recipient",
            content="Hello!"
        )
        self.servicer.messages.append(msg)
        
        request = chat_pb2.DeleteMessagesRequest(message_ids=[1])
        
        response = self.servicer.DeleteMessages(request, self.context)
        
        self.assertTrue(response.success)
        self.assertEqual(response.error_message, "")
        self.assertEqual(len(self.servicer.messages), 0)

    def test_list_accounts_success(self):
        """Test listing accounts"""
        # Setup test accounts
        self.servicer.accounts = {
            "user1": "pass1",
            "user2": "pass2",
            "test3": "pass3"
        }
        
        request = chat_pb2.ListAccountsRequest(pattern="user")
        
        response = self.servicer.ListAccounts(request, self.context)
        
        self.assertEqual(len(response.usernames), 2)
        self.assertIn("user1", response.usernames)
        self.assertIn("user2", response.usernames)
        self.assertEqual(response.error_message, "")

    def test_delete_account_success(self):
        """Test deleting account successfully"""
        # Setup test account and messages
        username = "testuser"
        password_hash = "hashed_password"
        self.servicer.accounts[username] = password_hash
        self.context.invocation_metadata.return_value = [('username', username)]
        
        # Add some messages for this user
        msg1 = chat_pb2.Message(id=1, sender=username, recipient="other", content="Hello")
        msg2 = chat_pb2.Message(id=2, sender="other", recipient=username, content="Hi")
        self.servicer.messages.extend([msg1, msg2])
        
        request = chat_pb2.DeleteAccountRequest(
            username=username,
            password_hash=password_hash
        )
        
        response = self.servicer.DeleteAccount(request, self.context)
        
        self.assertTrue(response.success)
        self.assertEqual(response.error_message, "")
        self.assertNotIn(username, self.servicer.accounts)
        self.assertEqual(len(self.servicer.messages), 0)

    def test_delete_account_wrong_password(self):
        """Test deleting account with wrong password"""
        username = "testuser"
        self.servicer.accounts[username] = "correct_hash"
        
        request = chat_pb2.DeleteAccountRequest(
            username=username,
            password_hash="wrong_hash"
        )
        
        response = self.servicer.DeleteAccount(request, self.context)
        
        self.assertFalse(response.success)
        self.assertEqual(response.error_message, "Invalid password")
        self.assertIn(username, self.servicer.accounts)

    def test_thread_safety(self):
        """Test thread safety of message operations"""
        # Setup accounts
        self.servicer.accounts["sender"] = "pass1"
        self.servicer.accounts["recipient"] = "pass2"
        
        # Mock authentication context
        mock_context = MagicMock()
        mock_context.invocation_metadata.return_value = [('username', 'sender')]

        def send_messages():
            for i in range(100):
                request = chat_pb2.SendMessageRequest(
                    recipient="recipient",
                    content=f"Message {i}"
                )
                response = self.servicer.SendMessage(request, mock_context)
                self.assertNotEqual(response.message_id, 0)
                self.assertEqual(response.error_message, "")

        # Create multiple threads to send messages simultaneously
        threads = [threading.Thread(target=send_messages) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify we have all messages (5 threads * 100 messages each)
        self.assertEqual(len(self.servicer.messages), 500)
        
        # Verify message contents and properties
        senders = set(msg.sender for msg in self.servicer.messages)
        recipients = set(msg.recipient for msg in self.servicer.messages)
        self.assertEqual(senders, {"sender"})
        self.assertEqual(recipients, {"recipient"})
        
        # Verify message IDs are unique
        message_ids = [msg.id for msg in self.servicer.messages]
        self.assertEqual(len(message_ids), len(set(message_ids)), "Message IDs should be unique")

    def test_thread_safety_create_account(self):
        """Test thread safety of account creation"""
        def create_accounts():
            for i in range(100):
                request = chat_pb2.CreateAccountRequest(
                    username=f"user{i}_{threading.current_thread().name}",
                    password_hash=f"pass{i}"
                )
                response = self.servicer.CreateAccount(request, self.context)
                self.assertTrue(response.success)
                self.assertEqual(response.error_message, "")

        # Create multiple threads to create accounts simultaneously
        threads = [threading.Thread(target=create_accounts, name=str(i)) for i in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify we have all accounts (5 threads * 100 accounts each)
        self.assertEqual(len(self.servicer.accounts), 500)
        
        # Verify no duplicate usernames
        usernames = list(self.servicer.accounts.keys())
        self.assertEqual(len(usernames), len(set(usernames)), "Usernames should be unique")

    def test_thread_safety_mark_read(self):
        """Test thread safety of marking messages as read"""
        # Setup test data
        recipient = "testuser"
        self.servicer.accounts[recipient] = "pass"
        self.context.invocation_metadata.return_value = [('username', recipient)]
        
        # Create test messages
        for i in range(500):
            msg = chat_pb2.Message(
                id=i+1,
                sender="sender",
                recipient=recipient,
                content=f"Message {i}",
                is_read=False
            )
            self.servicer.messages.append(msg)

        def mark_messages_read():
            for i in range(0, 500, 5):  # Each thread marks different messages
                request = chat_pb2.MarkReadRequest(
                    message_ids=list(range(i+1, i+6))  # Mark 5 messages at a time
                )
                response = self.servicer.MarkRead(request, self.context)
                self.assertTrue(response.success)
                self.assertEqual(response.error_message, "")

        # Create multiple threads to mark messages simultaneously
        threads = [threading.Thread(target=mark_messages_read) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify all messages are marked as read
        unread_messages = [msg for msg in self.servicer.messages if not msg.is_read]
        self.assertEqual(len(unread_messages), 0, "All messages should be marked as read")

    def test_thread_safety_delete_messages(self):
        """Test thread safety of message deletion"""
        # Setup test data
        recipient = "testuser"
        self.servicer.accounts[recipient] = "pass"
        self.context.invocation_metadata.return_value = [('username', recipient)]
        
        # Create test messages
        for i in range(500):
            msg = chat_pb2.Message(
                id=i+1,
                sender="sender",
                recipient=recipient,
                content=f"Message {i}"
            )
            self.servicer.messages.append(msg)

        def delete_messages():
            for i in range(0, 500, 5):  # Each thread deletes different messages
                request = chat_pb2.DeleteMessagesRequest(
                    message_ids=list(range(i+1, i+6))  # Delete 5 messages at a time
                )
                response = self.servicer.DeleteMessages(request, self.context)
                self.assertTrue(response.success)
                self.assertEqual(response.error_message, "")

        # Create multiple threads to delete messages simultaneously
        threads = [threading.Thread(target=delete_messages) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify all messages are deleted
        self.assertEqual(len(self.servicer.messages), 0, "All messages should be deleted")

    def test_thread_safety_delete_account(self):
        """Test thread safety of account deletion"""
        # Setup test accounts and messages
        for i in range(500):
            username = f"user{i}"
            password_hash = f"pass{i}"
            self.servicer.accounts[username] = password_hash
            
            # Add some messages for each user
            msg1 = chat_pb2.Message(id=i*2+1, sender=username, recipient="other", content="Hello")
            msg2 = chat_pb2.Message(id=i*2+2, sender="other", recipient=username, content="Hi")
            self.servicer.messages.extend([msg1, msg2])

        def delete_accounts():
            for i in range(100):  # Each thread deletes 100 accounts
                thread_id = int(threading.current_thread().name)
                base_index = thread_id * 100 + i
                username = f"user{base_index}"
                password_hash = f"pass{base_index}"
                
                request = chat_pb2.DeleteAccountRequest(
                    username=username,
                    password_hash=password_hash
                )
                self.context.invocation_metadata.return_value = [('username', username)]
                response = self.servicer.DeleteAccount(request, self.context)
                self.assertTrue(response.success)
                self.assertEqual(response.error_message, "")

        # Create multiple threads to delete accounts simultaneously
        threads = [threading.Thread(target=delete_accounts, name=str(i)) for i in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify all accounts and their messages are deleted
        self.assertEqual(len(self.servicer.accounts), 0, "All accounts should be deleted")
        self.assertEqual(len(self.servicer.messages), 0, "All messages should be deleted")

    def test_thread_safety_list_accounts(self):
        """Test thread safety of listing accounts while modifications occur"""
        # Setup initial accounts
        for i in range(100):
            self.servicer.accounts[f"user{i}"] = f"pass{i}"

        results = []
        def list_accounts():
            for _ in range(50):  # List accounts multiple times
                request = chat_pb2.ListAccountsRequest(pattern="user")
                response = self.servicer.ListAccounts(request, self.context)
                results.append((len(response.usernames), [int(user[4:]) for user in response.usernames].sort()[-1]))
        def modify_accounts():
            for i in range(100, 200):  # Add new accounts while listing
                request = chat_pb2.CreateAccountRequest(
                    username=f"user{i}",
                    password_hash=f"pass{i}"
                )
                self.servicer.CreateAccount(request, self.context)

        # Create threads for listing and modifying accounts simultaneously
        list_threads = [threading.Thread(target=list_accounts) for _ in range(3)]
        mod_threads = [threading.Thread(target=modify_accounts) for _ in range(2)]
        
        all_threads = list_threads + mod_threads
        for thread in all_threads:
            thread.start()
        for thread in all_threads:
            thread.join()

        # Verify final state
        self.assertEqual(len(self.servicer.accounts), 200)
        # Verify that no errors occurred during concurrent operations
        self.assertTrue(all(count == last_user + 1 for count, last_user in results))

    def test_grpc_metadata_invalid(self):
        """Test handling of invalid metadata"""
        # Setup context with invalid metadata
        self.context.invocation_metadata.return_value = [('invalid_key', 'value')]
        
        request = chat_pb2.SendMessageRequest(
            recipient="recipient",
            content="Hello!"
        )
        
        response = self.servicer.SendMessage(request, self.context)
        
        self.assertEqual(response.message_id, 0)
        self.assertEqual(response.error_message, "Not authenticated")

    def test_grpc_concurrent_connections(self):
        """Test handling multiple concurrent connections"""
        # Setup multiple mock contexts
        self.servicer.accounts["recipient"] = "pass"
        contexts = [MagicMock() for _ in range(10)]
        for i, ctx in enumerate(contexts):
            ctx.invocation_metadata.return_value = [('username', f'sender{i}')]
        
        def send_messages(context):
            for _ in range(50):
                request = chat_pb2.SendMessageRequest(
                    recipient="recipient",
                    content="Hello!"
                )
                response = self.servicer.SendMessage(request, context)
                self.assertNotEqual(response.message_id, 0)

        # Create and start threads with different contexts
        threads = [
            threading.Thread(target=send_messages, args=(ctx,))
            for ctx in contexts
        ]
        
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify all messages were sent
        self.assertEqual(len(self.servicer.messages), 500)

    def test_grpc_streaming_messages(self):
        """Test handling of streaming messages"""
        self.servicer.accounts["recipient"] = "pass"

        # Setup streaming context
        stream_context = MagicMock()
        stream_context.invocation_metadata.return_value = [('username', 'sender')]
        
        # Create messages
        messages = [
            chat_pb2.SendMessageRequest(
                recipient="recipient",
                content=f"Message {i}"
            ) for i in range(100)
        ]
        
        # Simulate streaming messages
        for msg in messages:
            response = self.servicer.SendMessage(msg, stream_context)
            self.assertNotEqual(response.message_id, 0)
        
        self.assertEqual(len(self.servicer.messages), 100)

    def test_grpc_bidirectional_streaming(self):
        """Test bidirectional streaming of messages"""
        self.servicer.accounts["user1"] = "pass"
        self.servicer.accounts["user2"] = "pass"

        # Setup streaming contexts
        context1 = MagicMock()
        context2 = MagicMock()
        context1.invocation_metadata.return_value = [('username', 'user1')]
        context2.invocation_metadata.return_value = [('username', 'user2')]
        
        def send_receive_messages(context, sender, recipient):
            for i in range(50):
                # Send message
                send_request = chat_pb2.SendMessageRequest(
                    recipient=recipient,
                    content=f"Message {i} from {sender}"
                )
                send_response = self.servicer.SendMessage(send_request, context)
                self.assertNotEqual(send_response.message_id, 0)
                
                # Get messages
                get_request = chat_pb2.GetMessagesRequest(include_read=True)
                self.servicer.GetMessages(get_request, context)

        # Create and start threads for both users
        thread1 = threading.Thread(
            target=send_receive_messages,
            args=(context1, 'user1', 'user2')
        )
        thread2 = threading.Thread(
            target=send_receive_messages,
            args=(context2, 'user2', 'user1')
        )
        
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # Verify messages
        self.assertEqual(len(self.servicer.messages), 100)

if __name__ == '__main__':
    unittest.main() 