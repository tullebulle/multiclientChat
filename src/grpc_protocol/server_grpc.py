"""
gRPC Chat Server Implementation

This module implements the server-side handling of the gRPC chat protocol.
It provides a high-performance, thread-safe server capable of handling multiple
simultaneous client connections using gRPC.
"""

import grpc
from concurrent import futures
import logging
from datetime import datetime
import time

from src.common.server_base import ChatServer
from . import chat_pb2
from . import chat_pb2_grpc

class ChatServicer(chat_pb2_grpc.ChatServiceServicer):
    """
    Implementation of the ChatService gRPC service.
    
    This class implements all the RPC methods defined in the chat.proto file.
    It uses the ChatServer base class for core functionality while providing
    the gRPC interface.
    """
    
    def __init__(self):
        self.messages = []  # Initialize empty messages list
        self.accounts = {}  # Store accounts directly in the servicer
    
    def CreateAccount(self, request, context):
        """Create a new user account"""
        try:
            # Check if username already exists (case-insensitive)
            username_lower = request.username.lower()
            for existing_username in self.accounts.keys():
                if existing_username.lower() == username_lower:
                    return chat_pb2.CreateAccountResponse(
                        success=False,
                        error_message="Username already exists"
                    )
            
            # Create new account
            self.accounts[request.username] = request.password_hash
            logging.info(f"Created new account for user: {request.username}")
            
            return chat_pb2.CreateAccountResponse(
                success=True,
                error_message=""
            )
        except Exception as e:
            return chat_pb2.CreateAccountResponse(
                success=False,
                error_message=str(e)
            )
    
    def Authenticate(self, request, context):
        """Authenticate a user"""
        try:
            username = request.username
            password_hash = request.password_hash
            
            # Check if user exists and password matches
            if (username in self.accounts and 
                self.accounts[username] == password_hash):
                logging.info(f"User authenticated successfully: {username}")
                return chat_pb2.AuthResponse(
                    success=True,
                    error_message=""
                )
                
            logging.warning(f"Failed authentication attempt for user: {username}")
            return chat_pb2.AuthResponse(
                success=False,
                error_message="Invalid username or password"
            )
            
        except Exception as e:
            logging.error(f"Authentication error: {e}")
            return chat_pb2.AuthResponse(
                success=False,
                error_message=str(e)
            )

    def SendMessage(self, request, context):
        """Send a message to another user"""
        username = self._get_username_from_metadata(context)
        if not username:
            return chat_pb2.SendMessageResponse(
                message_id=0,
                error_message="Not authenticated"
            )
            
        try:
            # Verify recipient exists
            if request.recipient not in self.accounts:
                return chat_pb2.SendMessageResponse(
                    message_id=0,
                    error_message="Recipient does not exist"
                )
            
            # Create and store the message
            msg_id = len(self.messages) + 1  # Simple ID generation
            msg = chat_pb2.Message(
                id=msg_id,
                sender=username,
                recipient=request.recipient,
                content=request.content,
                timestamp=int(time.time()),
                is_read=False
            )
            self.messages.append(msg)
            
            return chat_pb2.SendMessageResponse(
                message_id=msg_id,
                error_message=""
            )
        except Exception as e:
            return chat_pb2.SendMessageResponse(
                message_id=0,
                error_message=str(e)
            )

    def GetMessages(self, request: chat_pb2.GetMessagesRequest, context: grpc.ServicerContext) -> chat_pb2.GetMessagesResponse:
        """
        Get messages for the authenticated user.
        """
        username = self._get_username_from_metadata(context)
        if not username:
            return chat_pb2.GetMessagesResponse(
                messages=[],
                error_message="Not authenticated"
            )

        # Get messages for user
        messages = []
        for msg in self.messages:
            if msg.recipient == username:
                if request.include_read or not msg.is_read:
                    messages.append(msg)

        return chat_pb2.GetMessagesResponse(
            messages=messages,
            error_message=""
        )

    def _get_username_from_metadata(self, context: grpc.ServicerContext) -> str:
        """
        Extract username from the request metadata.
        
        Args:
            context: gRPC context containing metadata
            
        Returns:
            str: Username from metadata or empty string if not found
        """
        metadata = dict(context.invocation_metadata())
        return metadata.get('username', '')

    def MarkRead(self, request: chat_pb2.MarkReadRequest, context: grpc.ServicerContext) -> chat_pb2.MarkReadResponse:
        """Mark messages as read"""
        username = self._get_username_from_metadata(context)
        if not username:
            return chat_pb2.MarkReadResponse(
                success=False,
                error_message="Not authenticated"
            )
        
        try:
            # Mark messages as read if they belong to the user
            for message in self.messages:
                if message.id in request.message_ids and message.recipient == username:
                    message.is_read = True
            
            return chat_pb2.MarkReadResponse(
                success=True,
                error_message=""
            )
        except Exception as e:
            return chat_pb2.MarkReadResponse(
                success=False,
                error_message=str(e)
            )

    def DeleteMessages(self, request: chat_pb2.DeleteMessagesRequest, context: grpc.ServicerContext) -> chat_pb2.DeleteMessagesResponse:
        """Delete messages"""
        username = self._get_username_from_metadata(context)
        if not username:
            return chat_pb2.DeleteMessagesResponse(
                success=False,
                error_message="Not authenticated"
            )
        
        try:
            # Create a new list without the deleted messages
            original_length = len(self.messages)
            self.messages = [
                msg for msg in self.messages 
                if msg.id not in request.message_ids or msg.recipient != username
            ]
            
            # Verify messages were actually deleted
            if len(self.messages) == original_length:
                return chat_pb2.DeleteMessagesResponse(
                    success=False,
                    error_message="No messages found to delete"
                )
            
            return chat_pb2.DeleteMessagesResponse(
                success=True,
                error_message=""
            )
        except Exception as e:
            return chat_pb2.DeleteMessagesResponse(
                success=False,
                error_message=str(e)
            )

    def ListAccounts(self, request: chat_pb2.ListAccountsRequest, context: grpc.ServicerContext) -> chat_pb2.ListAccountsResponse:
        """List user accounts matching pattern"""
        try:
            usernames = list(self.accounts.keys())
            
            # Filter by pattern if provided
            if request.pattern and request.pattern != "*":
                usernames = [u for u in usernames if request.pattern in u]
            
            return chat_pb2.ListAccountsResponse(
                usernames=usernames,
                error_message=""
            )
        except Exception as e:
            return chat_pb2.ListAccountsResponse(
                usernames=[],
                error_message=str(e)
            )

    def DeleteAccount(self, request: chat_pb2.DeleteAccountRequest, context: grpc.ServicerContext) -> chat_pb2.DeleteAccountResponse:
        """Delete a user account"""
        try:
            username = request.username
            password_hash = request.password_hash
            logging.info(f"Received delete account request for user: {username}")
            
            # Log current accounts for debugging
            logging.debug(f"Current accounts: {list(self.accounts.keys())}")
            
            # Verify account exists and password matches
            if username not in self.accounts:
                logging.error(f"Account deletion failed: User {username} does not exist")
                return chat_pb2.DeleteAccountResponse(
                    success=False,
                    error_message="Account does not exist"
                )
                
            if self.accounts[username] != password_hash:
                logging.error(f"Account deletion failed: Invalid password for user {username}")
                return chat_pb2.DeleteAccountResponse(
                    success=False,
                    error_message="Invalid password"
                )
            
            # Delete the account
            del self.accounts[username]
            logging.info(f"Deleted account for user: {username}")
            
            # Delete all messages for this user
            original_message_count = len(self.messages)
            self.messages = [
                msg for msg in self.messages 
                if msg.sender != username and msg.recipient != username
            ]
            messages_deleted = original_message_count - len(self.messages)
            logging.info(f"Deleted {messages_deleted} messages for user: {username}")
            
            return chat_pb2.DeleteAccountResponse(
                success=True,
                error_message=""
            )
            
        except Exception as e:
            logging.error(f"Error during account deletion: {str(e)}", exc_info=True)
            return chat_pb2.DeleteAccountResponse(
                success=False,
                error_message=str(e)
            )

def serve(port=50051):
    """
    Start the gRPC server.
    
    Args:
        port: Port number to listen on
        
    The server runs until interrupted, handling requests using
    the ChatServicer implementation.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(
        ChatServicer(), server
    )
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    
    logging.info(f"gRPC Server started on port {port}")
    
    try:
        while True:
            time.sleep(86400)  # One day in seconds
    except KeyboardInterrupt:
        server.stop(0)
        logging.info("Server stopped")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    serve() 