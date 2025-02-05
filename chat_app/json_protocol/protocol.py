"""
JSON Protocol Implementation

Defines the JSON-based protocol for the chat application.
"""

import json
from enum import Enum, auto
from typing import Tuple, Dict, Any

class Command(Enum):
    """Available commands in the protocol"""
    ERROR = auto()
    CREATE_ACCOUNT = auto()
    AUTH = auto()
    LIST_ACCOUNTS = auto()
    SEND_MESSAGE = auto()
    GET_MESSAGES = auto()
    MARK_READ = auto()
    DELETE_MESSAGES = auto()
    DELETE_ACCOUNT = auto()

def encode_message(command: Command, payload: Dict[str, Any]) -> bytes:
    """
    Encode a message according to the JSON protocol.
    
    Args:
        command: The command to send
        payload: Dictionary containing the message payload
        
    Returns:
        bytes: The encoded message
    """
    message = {
        "command": command.name,
        "payload": payload
    }
    return json.dumps(message).encode('utf-8')

def decode_message(data: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Decode a message according to the JSON protocol.
    
    Args:
        data: The raw message data
        
    Returns:
        Tuple[str, dict]: The command and payload
    """
    try:
        message = json.loads(data.decode('utf-8'))
        
        if not isinstance(message, dict):
            raise ValueError("Message must be a JSON object")
            
        if "command" not in message:
            raise ValueError("Message missing 'command' field")
            
        if "payload" not in message:
            raise ValueError("Message missing 'payload' field")
            
        command = message["command"]
        
        # Validate command is a known command
        if not any(cmd.name == command for cmd in Command):
            raise ValueError(f"Unknown command: {command}")
            
        return command, message["payload"]
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}") 