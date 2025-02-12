"""
JSON Protocol Implementation

Defines the JSON-based protocol for the chat application.
"""

import json
from enum import Enum, auto
from typing import Tuple, Dict, Any
from ..common.commands import Command

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

        # Convert Command enum to string name for test compatibility
        command = message["command"]
        if isinstance(command, Command):
            command = command.name
        elif isinstance(command, str) and hasattr(Command, command):
            # Already a string name, leave it as is
            pass
        else:
            raise ValueError(f"Unknown command: {command}")
        
        return command, message["payload"]
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}") 