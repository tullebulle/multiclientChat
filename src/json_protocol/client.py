"""
JSON Protocol Chat Client

A command-line client using the JSON protocol for chat communication. This client
implements a human-readable protocol format while maintaining full chat functionality.

Features:
- JSON-based message format for readability
- Full chat functionality (messaging, accounts, status)
- Secure password handling with SHA-256 hashing
- Error handling with descriptive messages
- Session-based authentication

Protocol Structure:
- Messages are JSON objects
- Each message includes version, command, and payload
- Responses include status and relevant data
- Error responses include descriptive messages
"""

import socket
import logging
import json
from typing import Tuple, Dict, Any
from . import protocol
import hashlib

class JSONChatClient:
    """
    Interactive chat client using JSON protocol.
    
    This client implements the JSON-based protocol for human-readable
    communication with the chat server. It handles message formatting,
    command processing, and secure password handling.
    
    Attributes:
        host (str): Server hostname or IP address
        port (int): Server port number
        sock (socket): TCP socket connection to server
        current_user (str): Currently logged in username, if any
        
    The client maintains a single TCP connection and uses JSON formatting
    for all message exchanges.
    """
    
    def __init__(self, host: str = 'localhost', port: int = 9998):
        """
        Initialize the chat client.
        
        Args:
            host: Server hostname or IP address
            port: Server port number
            
        The client starts in a disconnected state. Use connect() to
        establish the server connection.
        """
        self.host = host
        self.port = port
        self.sock = None
        self.current_user = None
        
    def _hash_password(self, password: str) -> str:
        """
        Hash password using SHA-256.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hexadecimal representation of password hash
            
        Uses SHA-256 for consistent hashing across the application.
        The hash is transmitted instead of plain text passwords.
        """
        return hashlib.sha256(password.encode()).hexdigest()
        
    def connect(self, server_address=None):
        """
        Connect to the chat server.
        
        Args:
            server_address: Optional tuple of (host, port). If not provided,
                          uses defaults.
            
        Returns:
            bool: True if connection successful, False otherwise
            
        Establishes a TCP connection to the server. If server_address is
        provided, updates the stored host and port before connecting.
        """
        if server_address:
            self.host, self.port = server_address
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            return True
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from the server"""
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
            self.current_user = None
            
    def send_command(self, command: protocol.Command, payload: dict) -> tuple:
        """Send a command to the server and get the response"""
        if not self.sock:
            logging.error("Not connected to server")
            return None
            
        try:
            # Send command
            message = protocol.encode_message(command, payload)
            self.sock.sendall(message)
            
            # Get response
            response = self.sock.recv(4096)  # Larger buffer for JSON
            if not response:
                raise ConnectionError("Server closed connection")
            return self.decode_response(response)
        except Exception as e:
            logging.error(f"Error sending command: {e}")
            return None

    def decode_response(self, data: bytes) -> Tuple[str, Dict[str, Any]]:
        """Decode a response from the server"""
        try:
            message = json.loads(data.decode('utf-8'))
            
            if "version" not in message:
                raise ValueError("Missing protocol version")
            if message["version"] != protocol.PROTOCOL_VERSION:
                raise ValueError(f"Unsupported protocol version: {message['version']}")
            
            if "command" not in message:
                raise ValueError("Message missing 'command' field")
            
            if "payload" not in message:
                raise ValueError("Message missing 'payload' field")
            
            # Convert Command enum to string name for test compatibility
            command = message["command"]
            if isinstance(command, protocol.Command):
                command = command.name
            elif isinstance(command, str) and hasattr(protocol.Command, command):
                # Already a string name, leave it as is
                pass
            else:
                raise ValueError(f"Invalid command: {command}")
            
            return command, message["payload"]
        
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")

    def create_account(self, username: str, password: str) -> bool:
        """Create a new account
        
        Args:
            username: The username to create
            password: The password for the account
            
        Returns:
            bool: True if account was created successfully
        """
        # Hash password before sending
        password_hash = self._hash_password(password)
        
        payload = {
            "username": username,
            "password": password_hash
        }
        
        response = self.send_command(protocol.Command.CREATE_ACCOUNT, payload)
        if response:
            cmd, payload = response
            return payload.get("status") == "success"
        return False
                
    def login(self, username: str, password: str) -> bool:
        """Log in to an existing account
        
        Args:
            username: The username to log in as
            password: The account password
            
        Returns:
            bool: True if login was successful
        """
        # Hash password before sending
        password_hash = self._hash_password(password)
        
        payload = {
            "username": username,
            "password": password_hash
        }
        
        response = self.send_command(protocol.Command.AUTH, payload)
        if response:
            cmd, payload = response
            if payload.get("status") == "success":
                self.current_user = username
                return True
        return False
                
    def list_accounts(self, pattern: str = "*") -> list:
        """List accounts matching a pattern
        
        Args:
            pattern: Search pattern (default: "*" for all accounts)
            
        Returns:
            list: List of matching usernames, or None on error
        """
        payload = {
            "pattern": pattern
        }
        
        response = self.send_command(protocol.Command.LIST_ACCOUNTS, payload)
        if response:
            cmd, payload = response
            if payload.get("status") == "success":
                return payload.get("accounts", [])
        return None

    def send_message(self, recipient: str, content: str) -> int:
        """Send a message to another user
        
        Args:
            recipient: Username of the recipient
            content: Message content
            
        Returns:
            int: Message ID if successful, None on error
        """
        payload = {
            "recipient": recipient,
            "content": content
        }
        
        response = self.send_command(protocol.Command.SEND_MESSAGE, payload)
        if response:
            cmd, payload = response
            if payload.get("status") == "success":
                return payload.get("message_id")
        return None

    def get_messages(self, include_read: bool = True) -> list:
        """Get messages for the current user
        
        Args:
            include_read: Whether to include already read messages
            
        Returns:
            list: List of message dictionaries
        """
        payload = {
            "include_read": include_read
        }
        
        response = self.send_command(protocol.Command.GET_MESSAGES, payload)
        if response:
            cmd, payload = response
            if payload.get("status") == "success":
                return payload.get("messages", [])
        return None

    def mark_read(self, message_ids: list) -> int:
        """Mark messages as read
        
        Args:
            message_ids: List of message IDs to mark as read
            
        Returns:
            int: Number of messages marked as read
        """
        payload = {
            "message_ids": message_ids
        }
        
        response = self.send_command(protocol.Command.MARK_READ, payload)
        if response:
            cmd, payload = response
            if payload.get("status") == "success":
                return payload.get("marked_count", 0)
        return 0

    def delete_messages(self, message_ids: list) -> bool:
        """
        Delete specific messages
        
        Args:
            message_ids: List of message IDs to delete
            
        Returns:
            bool: True if successful
        """
        if not self.current_user:
            logging.error("Not logged in")
            return False
        
        response = self.send_command(protocol.Command.DELETE_MESSAGES, {
            "message_ids": message_ids
        })

        if response:
            cmd, result = response
            if cmd == protocol.Command.ERROR:
                logging.error(f"Failed to delete messages: {result.decode()}")
                return False
            return True
        return False

    def get_unread_count(self) -> int:
        """Get number of unread messages
        
        Returns:
            int: Number of unread messages
        """
        response = self.send_command(protocol.Command.GET_UNREAD_COUNT, {})
        if response:
            cmd, payload = response
            if payload.get("status") == "success":
                return payload.get("count", 0)
        return 0

    def delete_account(self, username: str, password: str) -> bool:
        """Delete an account
        
        Args:
            username: Username of account to delete
            password: Password for verification
            
        Returns:
            bool: True if account was deleted successfully
        """
        # Hash password before sending
        password_hash = self._hash_password(password)
        
        payload = {
            "username": username,
            "password": password_hash
        }
        
        response = self.send_command(protocol.Command.DELETE_ACCOUNT, payload)
        if response:
            cmd, payload = response
            return payload.get("status") == "success"
        return False

