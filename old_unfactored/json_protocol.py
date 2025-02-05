"""
Chat Application JSON Protocol Definition

This module defines the JSON-based wire protocol for the chat application.
It provides constants and utilities for message encoding/decoding.
"""

from enum import Enum
from typing import Dict, Any, Union, Tuple
import json

class Command(str, Enum):
    """Command types for the JSON protocol"""
    AUTH = "auth"
    CREATE_ACCOUNT = "create_account"
    SEND_MESSAGE = "send_message"
    RECEIVE_MESSAGE = "receive_message"
    LIST_ACCOUNTS = "list_accounts"
    DELETE_MESSAGE = "delete_message"
    DELETE_ACCOUNT = "delete_account"
    ERROR = "error"

def encode_message(command: Command, payload: Dict[str, Any]) -> bytes:
    """
    Encode a message according to the JSON protocol format.
    
    Args:
        command (Command): The command type
        payload (Dict[str, Any]): The message payload
        
    Returns:
        bytes: The encoded JSON message
    """
    message = {
        "command": command.value,
        "payload": payload
    }
    return json.dumps(message).encode('utf-8')

def decode_message(data: bytes) -> Tuple[Command, Dict[str, Any]]:
    """
    Decode a message according to the JSON protocol format.
    
    Args:
        data (bytes): The raw JSON message data
        
    Returns:
        Tuple[Command, Dict[str, Any]]: The command and payload
    """
    message = json.loads(data.decode('utf-8'))
    return Command(message["command"]), message["payload"]

# Example message structures:
AUTH_MESSAGE = {
    "command": "auth",
    "payload": {
        "username": "user123",
        "password_hash": "hash_value"
    }
}

SEND_MESSAGE = {
    "command": "send_message",
    "payload": {
        "recipient": "user456",
        "message": "Hello, how are you?",
        "timestamp": "2024-02-01T12:34:56Z"
    }
}

LIST_ACCOUNTS = {
    "command": "list_accounts",
    "payload": {
        "pattern": "user*",  # Optional wildcard pattern
        "page": 1,          # For pagination
        "page_size": 20     # Number of results per page
    }
} 