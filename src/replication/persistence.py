"""
Persistence Manager Module

This module provides persistence for the chat application using SQLite.
It handles storage and retrieval of user accounts, messages, and Raft consensus data.
"""

import sqlite3
import logging
import json
import os
import time
from typing import List, Dict, Tuple, Optional, Any, Union
from enum import Enum, auto

class CommandType(Enum):
    """Types of commands that can be applied to the state machine."""
    CREATE_ACCOUNT = auto()
    DELETE_ACCOUNT = auto()
    SEND_MESSAGE = auto()
    MARK_READ = auto()
    DELETE_MESSAGES = auto()

class PersistenceManager:
    """
    Manages persistence for the chat application.
    
    This class provides an interface for storing and retrieving data from
    an SQLite database, including user accounts, messages, and Raft consensus data.
    
    Attributes:
        db_path: Path to the SQLite database file
        conn: SQLite connection object
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the persistence manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        
        # Initialize tables
        self._init_tables()
        
        logging.info(f"Initialized persistence manager with database at {db_path}")
    
    def _init_tables(self):
        """Initialize database tables if they don't exist."""
        with self.conn:
            # Users table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL
                )
            """)
            
            # Messages table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (sender) REFERENCES users(username),
                    FOREIGN KEY (recipient) REFERENCES users(username)
                )
            """)
            
            # Raft log table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS raft_log (
                    log_index INTEGER PRIMARY KEY,
                    term INTEGER NOT NULL,
                    command_type INTEGER NOT NULL,
                    data TEXT NOT NULL
                )
            """)
            
            # Metadata table for storing Raft state
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
    
    # User management methods
    
    def create_user(self, username: str, password_hash: str) -> bool:
        """
        Create a new user account.
        
        Args:
            username: User's username
            password_hash: Hash of the user's password
            
        Returns:
            bool: True if account was created successfully, False otherwise
        """
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash)
                )
            logging.info(f"Created new user account: {username}")
            return True
        except sqlite3.IntegrityError:
            logging.warning(f"Failed to create user account: {username} (already exists)")
            return False
        except Exception as e:
            logging.error(f"Error creating user account: {e}")
            return False
    
    def authenticate_user(self, username: str, password_hash: str) -> bool:
        """
        Authenticate a user by checking username and password hash.
        
        Args:
            username: User's username
            password_hash: Hash of the user's password
            
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        try:
            cursor = self.conn.execute(
                "SELECT password_hash FROM users WHERE username = ?",
                (username,)
            )
            user = cursor.fetchone()
            
            if user and user['password_hash'] == password_hash:
                logging.info(f"User authenticated successfully: {username}")
                return True
            
            logging.warning(f"Failed authentication attempt for user: {username}")
            return False
        except Exception as e:
            logging.error(f"Error authenticating user: {e}")
            return False
    
    def list_users(self, pattern: Optional[str] = None) -> List[str]:
        """
        List users matching the given pattern.
        
        Args:
            pattern: SQL LIKE pattern to match against usernames (optional)
            
        Returns:
            List[str]: List of matching usernames
        """
        try:
            cursor = None
            if pattern and pattern != "*":
                cursor = self.conn.execute(
                    "SELECT username FROM users WHERE username LIKE ?",
                    (f"%{pattern}%",)
                )
            else:
                cursor = self.conn.execute("SELECT username FROM users")
            
            return [row['username'] for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Error listing users: {e}")
            return []
    
    def delete_user(self, username: str) -> bool:
        """
        Delete a user account.
        
        Args:
            username: Username of the account to delete
            
        Returns:
            bool: True if account was deleted successfully, False otherwise
        """
        try:
            with self.conn:
                # First check if user exists
                cursor = self.conn.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (username,)
                )
                if not cursor.fetchone():
                    logging.warning(f"Attempted to delete non-existent user: {username}")
                    return False
                
                # Delete user's messages
                self.conn.execute(
                    "DELETE FROM messages WHERE sender = ? OR recipient = ?",
                    (username, username)
                )
                
                # Delete user account
                self.conn.execute(
                    "DELETE FROM users WHERE username = ?",
                    (username,)
                )
            
            logging.info(f"Deleted user account: {username}")
            return True
        except Exception as e:
            logging.error(f"Error deleting user account: {e}")
            return False
    
    # Message management methods
    
    def add_message(self, sender: str, recipient: str, content: str) -> int:
        """
        Add a new message.
        
        Args:
            sender: Username of the sender
            recipient: Username of the recipient
            content: Message content
            
        Returns:
            int: ID of the new message, or 0 if failed
        """
        try:
            timestamp = int(time.time())
            
            with self.conn:
                cursor = self.conn.execute(
                    """
                    INSERT INTO messages (sender, recipient, content, timestamp, is_read)
                    VALUES (?, ?, ?, ?, 0)
                    """,
                    (sender, recipient, content, timestamp)
                )
            
            message_id = cursor.lastrowid
            logging.info(f"Added message {message_id} from {sender} to {recipient}")
            return message_id
        except Exception as e:
            logging.error(f"Error adding message: {e}")
            return 0
    
    def get_messages(self, username: str, include_read: bool = False) -> List[Dict[str, Any]]:
        """
        Get messages for a user.
        
        Args:
            username: Username of the recipient
            include_read: Whether to include messages that have been read
            
        Returns:
            List[Dict[str, Any]]: List of messages
        """
        try:
            query = """
                SELECT id, sender, recipient, content, timestamp, is_read
                FROM messages
                WHERE recipient = ?
            """
            
            if not include_read:
                query += " AND is_read = 0"
            
            cursor = self.conn.execute(query, (username,))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row['id'],
                    'sender': row['sender'],
                    'recipient': row['recipient'],
                    'content': row['content'],
                    'timestamp': row['timestamp'],
                    'is_read': bool(row['is_read'])
                })
            
            return messages
        except Exception as e:
            logging.error(f"Error getting messages: {e}")
            return []
    
    def mark_read(self, username: str, message_ids: List[int]) -> bool:
        """
        Mark messages as read.
        
        Args:
            username: Username of the message recipient
            message_ids: List of message IDs to mark as read
            
        Returns:
            bool: True if messages were marked successfully, False otherwise
        """
        if not message_ids:
            return True
        
        try:
            placeholders = ','.join(['?'] * len(message_ids))
            with self.conn:
                self.conn.execute(
                    f"""
                    UPDATE messages
                    SET is_read = 1
                    WHERE id IN ({placeholders}) AND recipient = ?
                    """,
                    message_ids + [username]
                )
            
            logging.info(f"Marked messages as read for {username}: {message_ids}")
            return True
        except Exception as e:
            logging.error(f"Error marking messages as read: {e}")
            return False
    
    def delete_messages(self, username: str, message_ids: List[int]) -> bool:
        """
        Delete messages.
        
        Args:
            username: Username of the message recipient
            message_ids: List of message IDs to delete
            
        Returns:
            bool: True if messages were deleted successfully, False otherwise
        """
        if not message_ids:
            return True
        
        try:
            placeholders = ','.join(['?'] * len(message_ids))
            with self.conn:
                self.conn.execute(
                    f"""
                    DELETE FROM messages
                    WHERE id IN ({placeholders}) AND recipient = ?
                    """,
                    message_ids + [username]
                )
            
            logging.info(f"Deleted messages for {username}: {message_ids}")
            return True
        except Exception as e:
            logging.error(f"Error deleting messages: {e}")
            return False
    
    def get_unread_count(self, username: str) -> int:
        """
        Get the number of unread messages for a user.
        
        Args:
            username: Username of the recipient
            
        Returns:
            int: Number of unread messages
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT COUNT(*) as count
                FROM messages
                WHERE recipient = ? AND is_read = 0
                """,
                (username,)
            )
            result = cursor.fetchone()
            return result['count'] if result else 0
        except Exception as e:
            logging.error(f"Error getting unread count: {e}")
            return 0
    
    # Raft log methods
    
    def append_log_entry(self, term: int, command_type: CommandType, data: Dict[str, Any], force_index: int = None) -> int:
        """
        Append an entry to the Raft log.
        
        Args:
            term: Current term number
            command_type: Type of command
            data: Command data as a dictionary
            force_index: Force a specific index (used for log replication from leader)
            
        Returns:
            int: Index of the new log entry, or 0 if failed
        """
        try:
            data_json = json.dumps(data)
            
            with self.conn:
                if force_index is not None:
                    # Check if entry already exists at this index
                    cursor = self.conn.execute(
                        "SELECT log_index FROM raft_log WHERE log_index = ?",
                        (force_index,)
                    )
                    
                    if cursor.fetchone():
                        # Entry already exists, update it
                        self.conn.execute(
                            """
                            UPDATE raft_log 
                            SET term = ?, command_type = ?, data = ?
                            WHERE log_index = ?
                            """,
                            (term, command_type.value, data_json, force_index)
                        )
                        logging.info(f"Updated existing log entry at index {force_index}, term {term}")
                    else:
                        # Insert with forced index
                        self.conn.execute(
                            """
                            INSERT INTO raft_log (log_index, term, command_type, data)
                            VALUES (?, ?, ?, ?)
                            """,
                            (force_index, term, command_type.value, data_json)
                        )
                        logging.info(f"Inserted log entry with forced index {force_index}, term {term}")
                    
                    return force_index
                else:
                    # Normal append, let SQLite generate the index
                    cursor = self.conn.execute(
                        """
                        INSERT INTO raft_log (term, command_type, data)
                        VALUES (?, ?, ?)
                        """,
                        (term, command_type.value, data_json)
                    )
                
                    log_index = cursor.lastrowid
                    logging.info(f"Appended log entry at index {log_index}, term {term}, command {command_type.name}")
                    return log_index
        except Exception as e:
            logging.error(f"Error appending log entry: {e}", exc_info=True)
            return 0
    
    def get_log_entry(self, index: int) -> Optional[Dict[str, Any]]:
        """
        Get a log entry by index.
        
        Args:
            index: Log entry index
            
        Returns:
            Optional[Dict[str, Any]]: Log entry or None if not found
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT log_index, term, command_type, data
                FROM raft_log
                WHERE log_index = ?
                """,
                (index,)
            )
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'index': row['log_index'],
                'term': row['term'],
                'command_type': CommandType(row['command_type']),
                'data': json.loads(row['data'])
            }
        except Exception as e:
            logging.error(f"Error getting log entry: {e}")
            return None
    
    def get_log_entries(self, start_index: int, end_index: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get a range of log entries.
        
        Args:
            start_index: Starting index (inclusive)
            end_index: Ending index (inclusive, optional)
            
        Returns:
            List[Dict[str, Any]]: List of log entries
        """
        try:
            query = """
                SELECT log_index, term, command_type, data
                FROM raft_log
                WHERE log_index >= ?
            """
            params = [start_index]
            
            if end_index is not None:
                query += " AND log_index <= ?"
                params.append(end_index)
            
            query += " ORDER BY log_index ASC"
            
            cursor = self.conn.execute(query, params)
            
            entries = []
            for row in cursor.fetchall():
                entries.append({
                    'index': row['log_index'],
                    'term': row['term'],
                    'command_type': CommandType(row['command_type']),
                    'data': json.loads(row['data'])
                })
            
            return entries
        except Exception as e:
            logging.error(f"Error getting log entries: {e}")
            return []
    
    def delete_logs_from(self, index: int) -> bool:
        """
        Delete all log entries from the given index onwards.
        
        Args:
            index: Starting index (inclusive)
            
        Returns:
            bool: True if logs were deleted successfully, False otherwise
        """
        try:
            with self.conn:
                self.conn.execute(
                    "DELETE FROM raft_log WHERE log_index >= ?",
                    (index,)
                )
            
            logging.info(f"Deleted log entries from index {index}")
            return True
        except Exception as e:
            logging.error(f"Error deleting log entries: {e}")
            return False
    
    def get_last_log_index_and_term(self) -> Tuple[int, int]:
        """
        Get the index and term of the last log entry.
        
        Returns:
            Tuple[int, int]: (last_index, last_term), (0, 0) if log is empty
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT log_index, term
                FROM raft_log
                ORDER BY log_index DESC
                LIMIT 1
                """
            )
            
            row = cursor.fetchone()
            if row:
                return (row['log_index'], row['term'])
            
            # Empty log
            return (0, 0)
        except Exception as e:
            logging.error(f"Error getting last log index and term: {e}")
            return (0, 0)
    
    # Metadata methods
    
    def save_metadata(self, key: str, value: Union[str, int, bool, Dict]) -> bool:
        """
        Save a metadata key-value pair.
        
        Args:
            key: Metadata key
            value: Metadata value (will be JSON-encoded)
            
        Returns:
            bool: True if metadata was saved successfully, False otherwise
        """
        try:
            # Convert value to JSON string if it's not already a string
            if not isinstance(value, str):
                value = json.dumps(value)
            
            with self.conn:
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO metadata (key, value)
                    VALUES (?, ?)
                    """,
                    (key, value)
                )
            
            logging.debug(f"Saved metadata {key}={value}")
            return True
        except Exception as e:
            logging.error(f"Error saving metadata: {e}")
            return False
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get a metadata value by key.
        
        Args:
            key: Metadata key
            default: Default value to return if key is not found
            
        Returns:
            Any: Metadata value (JSON-decoded if possible) or default
        """
        try:
            cursor = self.conn.execute(
                "SELECT value FROM metadata WHERE key = ?",
                (key,)
            )
            
            row = cursor.fetchone()
            if not row:
                return default
            
            value = row['value']
            
            # Try to parse as JSON, fall back to string if not valid JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logging.error(f"Error getting metadata: {e}")
            return default
    
    def set_current_term(self, term: int) -> bool:
        """
        Set the current Raft term.
        
        Args:
            term: Term number
            
        Returns:
            bool: True if term was set successfully
        """
        return self.save_metadata('current_term', term)
    
    def get_current_term(self) -> int:
        """
        Get the current Raft term.
        
        Returns:
            int: Current term number, 0 if not set
        """
        return int(self.get_metadata('current_term', 0))
    
    def set_voted_for(self, candidate_id: Optional[str]) -> bool:
        """
        Set the node ID that this node voted for in the current term.
        
        Args:
            candidate_id: ID of the candidate node, or None if no vote
            
        Returns:
            bool: True if vote was recorded successfully
        """
        return self.save_metadata('voted_for', candidate_id)
    
    def get_voted_for(self) -> Optional[str]:
        """
        Get the node ID that this node voted for in the current term.
        
        Returns:
            Optional[str]: Candidate ID, or None if no vote
        """
        return self.get_metadata('voted_for', None) 