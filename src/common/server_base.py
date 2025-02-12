"""
Common Chat Server Functionality

This module provides the core server functionality shared between different protocol
implementations. It includes:

1. User Management:
   - Account creation and authentication
   - Password hashing and verification
   - Online status tracking

2. Message Handling:
   - Message storage and retrieval
   - Read/unread status management
   - Message deletion
   - Thread-safe operations

3. Server Infrastructure:
   - Base TCP server implementation
   - Thread management for multiple clients
   - Shared state handling

The module is protocol-agnostic and serves as the foundation for both Custom Binary
and JSON protocol implementations.
"""

import socketserver
import threading
from typing import Dict, Set, Optional, List
import hashlib
import os
from dataclasses import dataclass
import logging
import fnmatch
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class User:
    """
    Represents a user in the chat system.
    
    This class maintains user state including authentication details and message status.
    The password is stored as a hash with a unique salt for security.
    
    Attributes:
        username: The user's unique identifier
        password_hash: Securely hashed version of the user's password
        salt: Random bytes used in password hashing for added security
        is_online: Current connection status of the user
        unread_messages: Count of unread messages for the user
    """
    username: str
    password_hash: bytes
    salt: bytes
    is_online: bool = False
    unread_messages: int = 0

@dataclass
class Message:
    """
    Represents a chat message.
    
    Each message has a unique ID and tracks its read status. Messages maintain
    their sender/recipient information and timestamp for ordering.
    
    Attributes:
        id: Unique message identifier
        sender: Username of the message sender
        recipient: Username of the intended recipient
        content: The actual message text
        timestamp: When the message was sent
        is_read: Whether the recipient has read the message
    """
    id: int
    sender: str
    recipient: str
    content: str
    timestamp: datetime
    is_read: bool = False

class ChatServer:
    """
    Main server class handling all chat operations.
    
    This class manages all server-side chat functionality including user accounts,
    message handling, and thread synchronization. It maintains thread-safe access
    to shared resources using locks.
    
    Attributes:
        users: Dictionary mapping usernames to User objects
        online_users: Set of currently connected usernames
        messages: List of all messages in the system
        next_message_id: Counter for generating unique message IDs
        message_lock: Lock for thread-safe message operations
    """
    
    def __init__(self):
        """Initialize the chat server state."""
        self.users: Dict[str, User] = {}
        self.online_users: Set[str] = set()
        self.messages: List[Message] = []
        self.next_message_id: int = 1
        self.message_lock = threading.Lock()  # For thread-safe message handling
    
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
            
        password_hash, _ = self.hash_password(password, user.salt)
        return password_hash == user.password_hash

    def list_accounts(self, pattern: str = "*", page: int = 1, page_size: int = 10) -> dict:
        """
        List accounts matching the given pattern with pagination.
        
        Args:
            pattern: Wildcard pattern to match usernames against
            page: Page number (1-based)
            page_size: Number of accounts per page
            
        Returns:
            dict containing:
                accounts: List of matching usernames for the requested page
                total_accounts: Total number of matching accounts
                total_pages: Total number of pages
        """
        matching_accounts = [
            username for username in self.users.keys()
            if fnmatch.fnmatch(username, pattern)
        ]
        matching_accounts.sort()
        
        total_accounts = len(matching_accounts)
        total_pages = (total_accounts + page_size - 1) // page_size
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        page_accounts = matching_accounts[start_idx:end_idx]
        
        return {
            "accounts": page_accounts,
            "total_accounts": total_accounts,
            "total_pages": total_pages
        }

    def send_message(self, sender: str, recipient: str, content: str) -> Optional[Message]:
        """
        Send a message from one user to another.
        
        Args:
            sender: Username of sender
            recipient: Username of recipient
            content: Message content
            
        Returns:
            Message object if successful, None if failed
            
        Raises:
            ValueError: If sender or recipient don't exist
        """
        if sender not in self.users:
            raise ValueError("Sender does not exist")
        if recipient not in self.users:
            raise ValueError("Recipient does not exist")
            
        with self.message_lock:
            message = Message(
                id=self.next_message_id,
                sender=sender,
                recipient=recipient,
                content=content,
                timestamp=datetime.now(),
                is_read=False
            )
            self.next_message_id += 1
            self.messages.append(message)
            
            # Update unread count for recipient
            if recipient != sender:  # Don't count self-messages as unread
                self.users[recipient].unread_messages += 1
            
            logging.info(f"Message sent from {sender} to {recipient}")
            return message
    
    def get_messages(self, username: str, include_read: bool = True) -> List[Message]:
        """
        Get messages for a user.
        
        Args:
            username: Username to get messages for
            include_read: Whether to include previously read messages
            
        Returns:
            List of messages where user is the recipient
        """
        if username not in self.users:
            raise ValueError("User does not exist")
            
        with self.message_lock:
            messages = [
                msg for msg in self.messages
                if msg.recipient == username  # Only messages TO this user
                and (include_read or not msg.is_read)
            ]
            return sorted(messages, key=lambda m: m.timestamp)
    
    def mark_messages_read(self, username: str, message_ids: List[int]) -> int:
        """
        Mark messages as read.
        
        Args:
            username: Username marking messages as read
            message_ids: List of message IDs to mark as read
            
        Returns:
            Number of messages marked as read
        """
        if username not in self.users:
            raise ValueError("User does not exist")
            
        count = 0
        with self.message_lock:
            for msg in self.messages:
                if (msg.recipient == username and 
                    msg.id in message_ids and 
                    not msg.is_read):
                    msg.is_read = True
                    count += 1
            
            # Update unread count
            self.users[username].unread_messages -= count
            
        return count
    
    def get_unread_count(self, username: str) -> int:
        """
        Get number of unread messages for a user.
        
        Args:
            username: Username to check
            
        Returns:
            Number of unread messages
        """
        if username not in self.users:
            raise ValueError("User does not exist")
            
        return self.users[username].unread_messages
    
    def delete_messages(self, username: str, message_ids: List[int]) -> int:
        """
        Delete messages for a user.
        
        Args:
            username: Username deleting messages
            message_ids: List of message IDs to delete
            
        Returns:
            Number of messages deleted
        """
        if username not in self.users:
            raise ValueError("User does not exist")
            
        count = 0
        with self.message_lock:
            # Count messages that will be deleted
            for msg in self.messages:
                if (msg.id in message_ids and
                    (msg.sender == username or msg.recipient == username)):
                    count += 1
            
            # Filter out deleted messages
            self.messages = [
                msg for msg in self.messages
                if not (
                    msg.id in message_ids and
                    (msg.sender == username or msg.recipient == username)
                )
            ]
            
            # Update unread count if necessary
            if count > 0:
                unread_deleted = len([
                    msg for msg in self.messages
                    if msg.id in message_ids and
                    msg.recipient == username and
                    not msg.is_read
                ])
                self.users[username].unread_messages -= unread_deleted
            
            logging.debug(f"Deleted {count} messages for user {username}")
            
        return count

    def delete_account(self, username: str, password: str) -> bool:
        """
        Delete a user account.
        
        Args:
            username: Username of account to delete
            password: Password for verification
            
        Returns:
            bool: True if account was deleted successfully
        """
        # Verify the user exists and password is correct
        if not self.authenticate(username, password):
            return False
        
        # Remove the user's messages
        with self.message_lock:
            self.messages = [msg for msg in self.messages 
                            if msg.sender != username and msg.recipient != username]
        
        # Remove the user
        if username in self.online_users:
            self.online_users.remove(username)
        del self.users[username]
        
        logging.info(f"Account deleted: {username}")
        return True

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Threaded TCP server to handle multiple clients."""
    allow_reuse_address = True
    
    def __init__(self, server_address, RequestHandlerClass):
        """Initialize server with a shared ChatServer instance"""
        super().__init__(server_address, RequestHandlerClass)
        self.chat_server = ChatServer() 