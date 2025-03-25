"""
Test Server Persistence

This script tests the persistence of the chat server by:
1. Starting a server
2. Creating a user and sending messages
3. Shutting down the server
4. Starting the server again
5. Verifying that the user and messages are still present
"""

import os
import sys
import time
import logging
import tempfile
import unittest
import grpc
import shutil
from threading import Thread
from concurrent import futures

# Add the parent directory to sys.path to allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from src.grpc_protocol.persistence import PersistenceManager
from src.grpc_protocol.server import ChatServicer
from src.grpc_protocol import chat_pb2, chat_pb2_grpc

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

class TestServerPersistence(unittest.TestCase):
    """Test case for server persistence"""
    
    def setUp(self):
        """Set up a test database directory before the test"""
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_server.db")
        logging.info(f"Using test database at {self.db_path}")
        
        # Set up gRPC server variables
        self.server = None
        self.server_thread = None
        self.port = 50051
    
    def tearDown(self):
        """Clean up after the test"""
        # Stop server if it's running
        if self.server:
            self.server.stop(0)
            if self.server_thread:
                self.server_thread.join(timeout=5.0)
        
        # Remove the temporary directory
        try:
            shutil.rmtree(self.test_dir)
        except Exception as e:
            logging.warning(f"Error deleting temporary directory: {e}")
    
    def start_server(self, db_path=None):
        """Start a gRPC server with the ChatServicer"""
        if db_path is None:
            db_path = self.db_path
            
        # Create a server with persistence
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        
        # Create a ChatServicer with a PersistenceManager
        servicer = ChatServicer(db_path=db_path)
        
        # Add the servicer to the server
        chat_pb2_grpc.add_ChatServiceServicer_to_server(servicer, self.server)
        
        # Start the server
        self.server.add_insecure_port(f'localhost:{self.port}')
        self.server.start()
        
        logging.info(f"Server started on localhost:{self.port}")
        
        # Start a thread to keep the server running
        self.server_thread = Thread(target=lambda: self.server.wait_for_termination())
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(1)
    
    def stop_server(self):
        """Stop the running server"""
        if self.server:
            self.server.stop(0)
            if self.server_thread:
                self.server_thread.join(timeout=5.0)
                self.server_thread = None
            self.server = None
            logging.info("Server stopped")
            
            # Give a moment for cleanup
            time.sleep(1)
    
    def get_client_stub(self):
        """Create a client stub for communicating with the server"""
        channel = grpc.insecure_channel(f'localhost:{self.port}')
        return chat_pb2_grpc.ChatServiceStub(channel), channel
    
    def test_server_persistence(self):
        """Test that data persists across server restarts"""
        # Step 1: Start the server for the first time
        self.start_server()
        
        # Step 2: Create a user and send messages
        stub, channel = self.get_client_stub()
        
        # Create test users
        alice_response = stub.CreateAccount(
            chat_pb2.CreateAccountRequest(username="alice", password_hash="hash1")
        )
        self.assertTrue(alice_response.success)
        
        bob_response = stub.CreateAccount(
            chat_pb2.CreateAccountRequest(username="bob", password_hash="hash2")
        )
        self.assertTrue(bob_response.success)
        
        # Authenticate as Alice
        auth_response = stub.Authenticate(
            chat_pb2.AuthRequest(username="alice", password_hash="hash1")
        )
        self.assertTrue(auth_response.success)
        
        # Send a message from Alice to Bob
        metadata = (('username', 'alice'),)
        message_response = stub.SendMessage(
            chat_pb2.SendMessageRequest(recipient="bob", content="Hello Bob!"),
            metadata=metadata
        )
        self.assertNotEqual(message_response.message_id, 0)
        
        # Authenticate as Bob
        auth_response = stub.Authenticate(
            chat_pb2.AuthRequest(username="bob", password_hash="hash2")
        )
        self.assertTrue(auth_response.success)
        
        # Send a message from Bob to Alice
        metadata = (('username', 'bob'),)
        message_response = stub.SendMessage(
            chat_pb2.SendMessageRequest(recipient="alice", content="Hello Alice!"),
            metadata=metadata
        )
        self.assertNotEqual(message_response.message_id, 0)
        
        # List all users to verify
        list_response = stub.ListAccounts(
            chat_pb2.ListAccountsRequest(pattern="*"),
            metadata=metadata
        )
        self.assertEqual(len(list_response.usernames), 2)
        self.assertIn("alice", list_response.usernames)
        self.assertIn("bob", list_response.usernames)
        
        # Check that Bob has a message from Alice
        messages_response = stub.GetMessages(
            chat_pb2.GetMessagesRequest(include_read=True),
            metadata=metadata
        )
        self.assertEqual(len(messages_response.messages), 1)
        self.assertEqual(messages_response.messages[0].sender, "alice")
        self.assertEqual(messages_response.messages[0].content, "Hello Bob!")
        
        # Close the channel
        channel.close()
        
        # Step 3: Shut down the server
        self.stop_server()
        
        # Step 4: Start the server again
        self.start_server()
        
        # Step 5: Verify that the data persisted
        stub, channel = self.get_client_stub()
        
        # Authenticate as Bob
        auth_response = stub.Authenticate(
            chat_pb2.AuthRequest(username="bob", password_hash="hash2")
        )
        self.assertTrue(auth_response.success)
        
        # List accounts to verify they persisted
        metadata = (('username', 'bob'),)
        list_response = stub.ListAccounts(
            chat_pb2.ListAccountsRequest(pattern="*"),
            metadata=metadata
        )
        self.assertEqual(len(list_response.usernames), 2)
        self.assertIn("alice", list_response.usernames)
        self.assertIn("bob", list_response.usernames)
        
        # Check that Bob still has a message from Alice
        messages_response = stub.GetMessages(
            chat_pb2.GetMessagesRequest(include_read=True),
            metadata=metadata
        )
        self.assertEqual(len(messages_response.messages), 1)
        self.assertEqual(messages_response.messages[0].sender, "alice")
        self.assertEqual(messages_response.messages[0].content, "Hello Bob!")
        
        # Authenticate as Alice
        auth_response = stub.Authenticate(
            chat_pb2.AuthRequest(username="alice", password_hash="hash1")
        )
        self.assertTrue(auth_response.success)
        
        # Check that Alice still has a message from Bob
        metadata = (('username', 'alice'),)
        messages_response = stub.GetMessages(
            chat_pb2.GetMessagesRequest(include_read=True),
            metadata=metadata
        )
        self.assertEqual(len(messages_response.messages), 1)
        self.assertEqual(messages_response.messages[0].sender, "bob")
        self.assertEqual(messages_response.messages[0].content, "Hello Alice!")
        
        # Close the channel
        channel.close()

if __name__ == "__main__":
    unittest.main() 