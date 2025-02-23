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
        self.chat_server = ChatServer()
    
    def CreateAccount(self, request, context):
        """
        Create a new user account.
        
        Args:
            request: CreateAccountRequest with username and password_hash
            context: gRPC context
            
        Returns:
            CreateAccountResponse with success status and error message if any
        """
        try:
            success = self.chat_server.create_account(
                request.username,
                request.password_hash
            )
            return chat_pb2.CreateAccountResponse(
                success=success,
                error_message="" if success else "Username already exists"
            )
        except Exception as e:
            return chat_pb2.CreateAccountResponse(
                success=False,
                error_message=str(e)
            )
    
    def Authenticate(self, request, context):
        """
        Authenticate a user.
        
        Args:
            request: AuthRequest with username and password_hash
            context: gRPC context
            
        Returns:
            AuthResponse with success status and error message if any
        """
        try:
            success = self.chat_server.authenticate(
                request.username,
                request.password_hash
            )
            return chat_pb2.AuthResponse(
                success=success,
                error_message="" if success else "Invalid credentials"
            )
        except Exception as e:
            return chat_pb2.AuthResponse(
                success=False,
                error_message=str(e)
            )

    def SendMessage(self, request, context):
        """
        Send a message to another user.
        
        Args:
            request: SendMessageRequest with recipient and content
            context: gRPC context
            
        Returns:
            SendMessageResponse with message ID and error message if any
        """
        try:
            # Get username from metadata
            metadata = dict(context.invocation_metadata())
            username = metadata.get('username')
            if not username:
                return chat_pb2.SendMessageResponse(
                    message_id=0,
                    error_message="Not authenticated"
                )
            
            message = self.chat_server.send_message(
                username,
                request.recipient,
                request.content
            )
            return chat_pb2.SendMessageResponse(
                message_id=message.id,
                error_message=""
            )
        except Exception as e:
            return chat_pb2.SendMessageResponse(
                message_id=0,
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