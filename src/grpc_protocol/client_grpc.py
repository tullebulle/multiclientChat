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
    
    def __init__(self, host='localhost', port=50051):
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
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
        
    def create_account(self, username: str, password: str) -> tuple[bool, str]:
        """
        Create a new account.
        
        Args:
            username: Desired username
            password: Password for the account
            
        Returns:
            tuple[bool, str]: (success, error_message)
        """
        try:
            password_hash = self._hash_password(password)
            request = chat_pb2.CreateAccountRequest(
                username=username,
                password_hash=password_hash
            )
            response = self.stub.CreateAccount(request)
            return response.success, response.error_message
        except grpc.RpcError as e:
            return False, str(e)
            
    def login(self, username: str, password: str) -> tuple[bool, str]:
        """
        Log in to an existing account.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            tuple[bool, str]: (success, error_message)
        """
        try:
            password_hash = self._hash_password(password)
            request = chat_pb2.AuthRequest(
                username=username,
                password_hash=password_hash
            )
            response = self.stub.Authenticate(request)
            if response.success:
                self.current_user = username
            return response.success, response.error_message
        except grpc.RpcError as e:
            return False, str(e)
            
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
            
        try:
            # Add authentication metadata
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
            
    def get_messages(self, include_read: bool = True) -> tuple[list, str]:
        """
        Get messages for the current user.
        
        Args:
            include_read: Whether to include read messages
            
        Returns:
            tuple[list, str]: (messages, error_message)
        """
        if not self.current_user:
            return [], "Not authenticated"
            
        try:
            metadata = [('username', self.current_user)]
            request = chat_pb2.GetMessagesRequest(
                include_read=include_read
            )
            response = self.stub.GetMessages(
                request,
                metadata=metadata
            )
            messages = [
                {
                    'id': msg.id,
                    'sender': msg.sender,
                    'content': msg.content,
                    'timestamp': msg.timestamp,
                    'is_read': msg.is_read
                }
                for msg in response.messages
            ]
            return messages, response.error_message
        except grpc.RpcError as e:
            return [], str(e)