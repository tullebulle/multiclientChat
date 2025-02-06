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
    GET_UNREAD_COUNT = auto()

PROTOCOL_VERSION = 1

def encode_message(command: Command, payload: dict) -> bytes:
    """Encode a message to send over the network"""
    message = {
        "version": PROTOCOL_VERSION,
        "command": command.name,
        "payload": payload
    }
    return json.dumps(message).encode('utf-8')

def decode_message(data: bytes) -> Tuple[Command, Dict[str, Any]]:
    """Decode a received message"""
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