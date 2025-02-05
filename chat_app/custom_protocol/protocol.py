"""
Custom Binary Protocol Implementation

Defines the binary protocol for the chat application.
"""

from enum import Enum, auto, IntEnum
import struct
from typing import Tuple, Optional

class Command(IntEnum):
    """Command codes for the custom protocol"""
    ERROR = 0
    CREATE_ACCOUNT = 1
    AUTH = 2
    LIST_ACCOUNTS = 3
    SEND_MESSAGE = 4
    GET_MESSAGES = 5
    MARK_READ = 6
    DELETE_MESSAGES = 7
    DELETE_ACCOUNT = 8
    GET_UNREAD_COUNT = 9

def encode_message(command: Command, payload: bytes) -> bytes:
    """
    Encode a message according to the binary protocol.
    Format: [command:1][length:2][payload:length]
    
    Args:
        command: The command to send
        payload: Raw bytes of the payload
        
    Returns:
        The encoded message as bytes
    """
    length = len(payload)
    header = struct.pack('!BH', command.value, length)
    return header + payload

def decode_message(data: bytes) -> Tuple[Command, bytes]:
    """
    Decode a message according to the binary protocol.
    
    Args:
        data: The raw message data
        
    Returns:
        Tuple of (command, payload)
        
    Raises:
        ValueError: If message format is invalid
    """
    if len(data) < 3:  # Command (1) + Length (2)
        raise ValueError("Message too short")
        
    command_val, length = struct.unpack('!BH', data[:3])
    
    try:
        command = Command(command_val)
    except ValueError:
        raise ValueError(f"Invalid command value: {command_val}")
        
    if len(data) < 3 + length:
        raise ValueError("Incomplete message")
        
    payload = data[3:3+length]
    return command, payload 