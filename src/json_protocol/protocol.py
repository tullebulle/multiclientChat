"""
JSON Protocol Implementation

This module defines a JSON-based protocol for chat communication. The protocol
prioritizes human readability and ease of debugging while maintaining full
functionality.

Protocol Structure:
1. Message Format:
   {
     "version": int,      # Protocol version number
     "command": string,   # Command name from Command enum
     "payload": object    # Command-specific data
   }

2. Size Constraints:
   - Maximum message size: 65539 bytes (matching binary protocol)
   - No fixed header size (JSON overhead)
   - UTF-8 encoding for text

3. Command Types:
   - Account management (CREATE_ACCOUNT, AUTH, DELETE_ACCOUNT)
   - Messaging (SEND_MESSAGE, GET_MESSAGES)
   - Status (GET_UNREAD_COUNT)
   - Error handling (ERROR)

4. Response Format:
   - Success responses include status and relevant data
   - Error responses include error message and status
"""

import json
from enum import Enum, auto
from typing import Tuple, Dict, Any

class Command(Enum):
    """
    Available commands in the protocol.
    
    Each command represents a specific operation in the chat system.
    Commands are sent as strings in the JSON protocol for readability.
    
    Commands:
        ERROR: Indicates an error condition
        CREATE_ACCOUNT: Create a new user account
        AUTH: Authenticate an existing user
        LIST_ACCOUNTS: Get list of users
        SEND_MESSAGE: Send a message to another user
        GET_MESSAGES: Retrieve messages
        MARK_READ: Mark messages as read
        DELETE_MESSAGES: Remove messages
        DELETE_ACCOUNT: Remove a user account
        GET_UNREAD_COUNT: Get number of unread messages
    """
    ERROR = auto()
    CREATE_ACCOUNT = auto()
    AUTH = auto()
    LIST_ACCOUNTS = auto()
    SEND_MESSAGE = auto()
    GET_MESSAGES = auto()
    MARK_READ = auto()
    DELETE_MESSAGES = auto()
    DELETE_ACCOUNT = auto()
    GET_UNREAD_COUNT = auto()

PROTOCOL_VERSION = 1

def encode_message(command: Command, payload: dict) -> bytes:
    """
    Encode a message to send over the network.
    
    Creates a JSON message with protocol version, command, and payload.
    
    Args:
        command: The command to send (from Command enum)
        payload: Dictionary containing command-specific data
        
    Returns:
        bytes: UTF-8 encoded JSON message
        
    The message is formatted as a JSON object with required fields
    and encoded as UTF-8 bytes for transmission.
    """
    message = {
        "version": PROTOCOL_VERSION,
        "command": command.name,
        "payload": payload
    }
    return json.dumps(message).encode('utf-8')

def decode_message(data: bytes) -> Tuple[Command, Dict[str, Any]]:
    """
    Decode a received message.
    
    Parses a JSON message and validates its structure and content.
    
    Args:
        data: UTF-8 encoded JSON message
        
    Returns:
        Tuple[Command, Dict[str, Any]]: The command and payload
        
    Raises:
        ValueError: If message format is invalid, version unsupported,
                   or required fields are missing
        
    Validates:
    1. JSON format
    2. Protocol version
    3. Required fields
    4. Command validity
    """
    try:
        message = json.loads(data.decode('utf-8'))
        
        if "version" not in message:
            raise ValueError("Missing protocol version")
        if message["version"] != PROTOCOL_VERSION:
            raise ValueError(f"Unsupported protocol version: {message['version']}")
            
        if "command" not in message:
            raise ValueError("Message missing 'command' field")
            
        if "payload" not in message:
            raise ValueError("Message missing 'payload' field")
            
        command_str = message["command"]
        
        # Convert string to Command enum
        try:
            command = Command[command_str]  # Get the actual enum
            return command, message["payload"]  # Return the enum
        except KeyError:
            raise ValueError(f"Unknown command: {command_str}")
            
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}") 