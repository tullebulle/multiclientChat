"""
Chat Application Server

This module implements the server-side functionality for the chat application.
It handles client connections, authentication, and message routing.
"""

import socketserver
import threading
from typing import Dict, Set, Optional
import hashlib
import os
from dataclasses import dataclass
import protocol
import json_protocol
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class User:
    """
    Represents a user in the chat system.
    
    Attributes:
        username: The user's unique username
        password_hash: Hashed version of the user's password
        salt: Random salt used in password hashing
        is_online: Current user's connection status
    """
    username: str
    password_hash: bytes
    salt: bytes
    is_online: bool = False

class ChatServer:
    """
    Main server class handling all chat operations.
    
    Attributes:
        users (Dict[str, User]): Dictionary of registered users
        online_users (Set[str]): Set of currently connected usernames
    """
    
    def __init__(self):
        """Initialize the chat server state."""
        self.users: Dict[str, User] = {}
        self.online_users: Set[str] = set()
    
    def hash_password(self, password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
        """
        Hash a password using PBKDF2 with SHA256.
        
        Args:
            password: The password to hash
            salt: Optional salt bytes. If None, generates new salt
            
        Returns:
            Tuple of (password_hash, salt)
        """
        if salt is None:
            salt = os.urandom(32)
        # Use 100,000 iterations of PBKDF2
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        return key, salt
    
    def create_account(self, username: str, password: str) -> bool:
        """
        Create a new user account.
        
        Args:
            username: Desired username
            password: User's password
            
        Returns:
            bool: True if account created successfully, False if username taken
        """
        if username in self.users:
            return False
            
        password_hash, salt = self.hash_password(password)
        self.users[username] = User(
            username=username,
            password_hash=password_hash,
            salt=salt
        )
        logging.info(f"Created new account for user: {username}")
        return True
    
    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate a user's credentials.
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            bool: True if authentication successful
        """
        user = self.users.get(username)
        if not user:
            return False
            
        # Hash the provided password with the user's salt
        password_hash, _ = self.hash_password(password, user.salt)
        return password_hash == user.password_hash

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Threaded TCP server to handle multiple clients."""
    allow_reuse_address = True
    
    def __init__(self, server_address, RequestHandlerClass):
        """Initialize server with a shared ChatServer instance"""
        super().__init__(server_address, RequestHandlerClass)
        self.chat_server = ChatServer()  # Shared chat server instance

class ChatRequestHandler(socketserver.BaseRequestHandler):
    def setup(self):
        """Get reference to the shared chat server instance"""
        self.chat_server = self.server.chat_server
        self.current_user = None
    
    def handle_custom_protocol(self, command: protocol.Command, payload: bytes):
        """
        Handle messages using custom protocol.
        
        Args:
            command: The command type
            payload: Raw bytes of the message payload
        """
        try:
            if command == protocol.Command.CREATE_ACCOUNT:
                # First byte is username length
                username_len = payload[0]
                username = payload[1:username_len+1].decode('utf-8')
                password = payload[username_len+1:].decode('utf-8')  # Changed: decode password from bytes
                
                success = self.chat_server.create_account(username, password)
                response = protocol.encode_message(
                    protocol.Command.CREATE_ACCOUNT,
                    b'\x01' if success else b'\x00'
                )
                self.request.send(response)
                
            elif command == protocol.Command.AUTH:
                username_len = payload[0]
                username = payload[1:username_len+1].decode('utf-8')
                password_hash = payload[username_len+1:].decode('utf-8')  # Changed: decode password_hash
                
                success = self.chat_server.authenticate(username, password_hash)
                if success:
                    self.current_user = username
                    response = protocol.encode_message(command, b'\x01')  # Success
                else:
                    response = protocol.encode_message(command, b'\x00')  # Failure
                    
                self.request.send(response)
                
            else:
                # Ensure user is authenticated for other commands
                if not self.current_user:
                    response = protocol.encode_message(
                        protocol.Command.ERROR,
                        b'Not authenticated'
                    )
                    self.request.send(response)
                    return
                
                # Handle other commands here...
                logging.info(f"Received command {command} from {self.current_user}")
                
        except Exception as e:
            logging.error(f"Error handling custom protocol: {e}")
            response = protocol.encode_message(
                protocol.Command.ERROR,
                str(e).encode('utf-8')
            )
            self.request.send(response)
    
    def handle_json_protocol(self, command: str, payload: dict):
        """
        Handle messages using JSON protocol.
        
        Args:
            command: The command type
            payload: Dictionary containing the message payload
        """
        try:
            if command == json_protocol.Command.AUTH:
                success = self.chat_server.authenticate(
                    payload['username'],
                    payload['password_hash']
                )
                if success:
                    self.current_user = payload['username']
                    response = {
                        'status': 'success',
                        'message': 'Authentication successful'
                    }
                else:
                    response = {
                        'status': 'error',
                        'message': 'Authentication failed'
                    }
                    
            elif command == json_protocol.Command.CREATE_ACCOUNT:
                success = self.chat_server.create_account(
                    payload['username'],
                    payload['password']
                )
                response = {
                    'status': 'success' if success else 'error',
                    'message': 'Account created' if success else 'Username taken'
                }
                
            else:
                # Ensure user is authenticated for other commands
                if not self.current_user:
                    response = {
                        'status': 'error',
                        'message': 'Not authenticated'
                    }
                else:
                    # Handle other commands here...
                    logging.info(f"Received command {command} from {self.current_user}")
                    response = {
                        'status': 'error',
                        'message': 'Command not implemented'
                    }
                    
            self.request.send(json_protocol.encode_message(
                command,
                response
            ))
            
        except Exception as e:
            logging.error(f"Error handling JSON protocol: {e}")
            response = {
                'status': 'error',
                'message': str(e)
            }
            self.request.send(json_protocol.encode_message(
                json_protocol.Command.ERROR,
                response
            ))

    def handle(self):
        """Handle incoming client connection."""
        logging.info(f"New connection from {self.client_address}")
        
        while True:
            try:
                # Receive data from client
                data = self.request.recv(1024)
                if not data:
                    break
                    
                # Try to decode as custom protocol first
                try:
                    command, payload = protocol.decode_message(data)
                    self.handle_custom_protocol(command, payload)
                except Exception as e:
                    logging.debug(f"Not a custom protocol message: {e}")
                    # Fall back to JSON protocol
                    try:
                        command, payload = json_protocol.decode_message(data)
                        self.handle_json_protocol(command, payload)
                    except Exception as e:
                        logging.error(f"Failed to decode message: {e}")
                        # Send error response
                        error_response = json_protocol.encode_message(
                            json_protocol.Command.ERROR,
                            {"status": "error", "message": "Invalid message format"}
                        )
                        self.request.send(error_response)
                        
            except Exception as e:
                logging.error(f"Error handling client: {e}")
                try:
                    error_response = json_protocol.encode_message(
                        json_protocol.Command.ERROR,
                        {"status": "error", "message": str(e)}
                    )
                    self.request.send(error_response)
                except:
                    pass  # Connection might be closed
                break
                
        logging.info(f"Connection closed from {self.client_address}")

def main():
    """Main entry point for the chat server."""
    host = "localhost"
    port = 9999
    
    server = ThreadedTCPServer((host, port), ChatRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    
    try:
        logging.info(f"Server starting on {host}:{port}")
        server_thread.start()
        server_thread.join()
    except KeyboardInterrupt:
        logging.info("Server shutting down...")
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    main()