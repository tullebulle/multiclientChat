"""
gRPC Chat Client Implementation

This module implements the client-side handling of the gRPC chat protocol.
It provides a clean interface to the chat service using generated gRPC stubs.
"""

import grpc
import logging
import hashlib
from datetime import datetime

from . import chat_pb2
from . import chat_pb2_grpc

class GRPCChatClient:
    """
    Chat client using gRPC protocol.
    
    This client uses generated gRPC stubs to communicate with the server,
    providing a high-level interface to all chat functionality.
    
    Attributes:
        channel: gRPC channel to server
        stub: Generated service stub
        current_user: Currently authenticated username
    """
    
    def __init__(self, host='localhost', port=9999):
        """
        Initialize the chat client.
        
        Args:
            host: Server hostname
            port: Server port number
        """
        self.channel = None
        self.stub = None
        self.current_user = None
        self.host = host
        self.port = port
        
    def connect(self):
        """
        Connect to the gRPC server.
        
        Returns:
            bool: True if connection successful
        """
        try:
            self.channel = grpc.insecure_channel(f'{self.host}:{self.port}')
            self.stub = chat_pb2_grpc.ChatServiceStub(self.channel)
            return True
        except Exception as e:
            logging.error(f"Failed to connect: {e}")
            return False
            
    def disconnect(self):
        """Close the gRPC channel"""
        if self.channel:
            self.channel.close()
            
    def _hash_password(self, password: str) -> str:
        """
        Hash password using SHA-256.
        Returns hex string representation of hash.
        """
        hasher = hashlib.sha256()
        hasher.update(password.encode('utf-8'))
        return hasher.hexdigest()  # Return hex string instead of raw bytes
        
    def create_account(self, username: str, password: str) -> tuple[bool, str]:
        """
        Create a new user account.
        
        Args:
            username: Username for new account
            password: Password for new account
            
        Returns:
            tuple[bool, str]: (success, error_message)
        """
        try:
            # Hash the password
            password_hash = self._hash_password(password)
            
            # Create request
            request = chat_pb2.CreateAccountRequest(
                username=username,
                password_hash=password_hash
            )
            
            # Send request
            response = self.stub.CreateAccount(request)
            
            # Check response
            if not response.success:
                logging.error(f"Failed to create account: {response.error_message}")
                return False, response.error_message
                
            return response.success, response.error_message
            
        except grpc.RpcError as e:
            error_msg = str(e)
            logging.error(f"Error creating account: {error_msg}")
            return False, error_msg
            
    def login(self, username: str, password: str) -> bool:
        """
        Login with username and password.
        
        Args:
            username: Username to login with
            password: Password to login with
            
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # Hash the password
            password_hash = self._hash_password(password)
            
            # Create request
            request = chat_pb2.AuthRequest(
                username=username,
                password_hash=password_hash
            )
            
            # Send request
            response = self.stub.Authenticate(request)
            
            if response.success:
                self.current_user = username
                logging.info(f"Logged in as: {username}")
                return True
                
            logging.error(f"Login failed: {response.error_message}")
            return False
            
        except grpc.RpcError as e:
            logging.error(f"Login error: {e}")
            return False
            
    def send_message(self, recipient: str, content: str) -> tuple[int, str]:
        """
        Send a message to another user.
        
        Args:
            recipient: Username of recipient
            content: Message content
            
        Returns:
            tuple[int, str]: (message_id, error_message)
        """
        if not self.current_user:
            return 0, "Not authenticated"
            
        # Add input validation
        if not recipient:
            return 0, "Recipient cannot be empty"
        if not content:
            return 0, "Message content cannot be empty"
            
        try:
            metadata = [('username', self.current_user)]
            request = chat_pb2.SendMessageRequest(
                recipient=recipient,
                content=content
            )
            response = self.stub.SendMessage(
                request,
                metadata=metadata
            )
            return response.message_id, response.error_message
        except grpc.RpcError as e:
            return 0, str(e)
            
    def get_messages(self, include_read: bool = True) -> list[dict]:
        """
        Get messages for the current user.
        
        Args:
            include_read: Whether to include read messages
            
        Returns:
            list[dict]: List of message dictionaries
        """
        if not self.current_user:
            return []
            
        try:
            metadata = [('username', self.current_user)]
            request = chat_pb2.GetMessagesRequest(
                include_read=include_read
            )
            response = self.stub.GetMessages(
                request,
                metadata=metadata
            )
            
            # Convert protobuf messages to dictionaries
            messages = []
            for msg in response.messages:
                if include_read or not msg.is_read:
                    messages.append({
                        'id': msg.id,
                        'sender': msg.sender,
                        'recipient': msg.recipient,
                        'content': msg.content,
                        'timestamp': int(msg.timestamp),  # Ensure timestamp is an integer
                        'is_read': msg.is_read
                    })
            return messages
        except grpc.RpcError as e:
            logging.error(f"Error getting messages: {e}")
            return []

    def mark_read(self, message_ids: list[int]) -> tuple[bool, str]:
        """
        Mark messages as read.
        
        Args:
            message_ids: List of message IDs to mark as read
            
        Returns:
            tuple[bool, str]: (success, error_message)
        """
        if not self.current_user:
            return False, "Not authenticated"
            
        try:
            metadata = [('username', self.current_user)]
            request = chat_pb2.MarkReadRequest(
                message_ids=message_ids
            )
            response = self.stub.MarkRead(
                request,
                metadata=metadata
            )
            return response.success, response.error_message
        except grpc.RpcError as e:
            return False, str(e)

    def delete_messages(self, message_ids: list[int]) -> tuple[bool, str]:
        """
        Delete messages.
        
        Args:
            message_ids: List of message IDs to delete
            
        Returns:
            tuple[bool, str]: (success, error_message)
        """
        if not self.current_user:
            return False, "Not authenticated"
            
        try:
            metadata = [('username', self.current_user)]
            request = chat_pb2.DeleteMessagesRequest(
                message_ids=message_ids
            )
            response = self.stub.DeleteMessages(
                request,
                metadata=metadata
            )
            return response.success, response.error_message
        except grpc.RpcError as e:
            return False, str(e)

    def list_accounts(self, pattern: str = "*") -> list[str]:
        """
        List user accounts matching a pattern.
        
        Args:
            pattern: Pattern to match usernames against
            
        Returns:
            list[str]: List of usernames (empty list if error)
        """
        try:
            metadata = [('username', self.current_user)] if self.current_user else []
            request = chat_pb2.ListAccountsRequest(
                pattern=pattern
            )
            response = self.stub.ListAccounts(
                request,
                metadata=metadata
            )
            # Convert protobuf repeated field to list and return just the usernames
            return list(response.usernames)
        except grpc.RpcError as e:
            logging.error(f"Error listing accounts: {e}")
            return []  # Return empty list on error

    def delete_account(self, username: str, password: str) -> bool:
        """
        Delete a user account.
        
        Args:
            username: Username of account to delete
            password: Password for account
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"Attempting to delete account for user: {username}")
            
            # Hash the password
            password_hash = self._hash_password(password)
            logging.debug(f"Generated password hash for deletion request")
            
            # Create request
            request = chat_pb2.DeleteAccountRequest(
                username=username,
                password_hash=password_hash
            )
            
            # Send request with metadata if logged in
            metadata = [('username', self.current_user)] if self.current_user else []
            logging.debug(f"Sending delete request with metadata: {metadata}")
            
            response = self.stub.DeleteAccount(request, metadata=metadata)
            
            if response.success:
                logging.info(f"Successfully deleted account: {username}")
                # If we're deleting our own account, clear current user
                if self.current_user == username:
                    self.current_user = None
                    logging.debug("Cleared current user after self-deletion")
                return True
            else:
                logging.error(f"Failed to delete account: {response.error_message}")
                return False
            
        except grpc.RpcError as e:
            logging.error(f"gRPC error while deleting account: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error while deleting account: {str(e)}", exc_info=True)
            return False