"""
Custom Binary Protocol Implementation

This module defines a compact and efficient binary protocol for chat communication.
The protocol is designed for minimal overhead while maintaining reliability and
ease of implementation.

Protocol Structure:
1. Message Format:
   [version:1][command:1][length:2][payload:length]
   - version: Protocol version (1 byte)
   - command: Command code (1 byte)
   - length: Payload length (2 bytes, unsigned short)
   - payload: Variable length data

2. Size Constraints:
   - Maximum payload size: 65535 bytes (2^16 - 1)
   - Fixed header size: 4 bytes
   - Total maximum message size: 65539 bytes

3. Command Types:
   - Account management (CREATE, AUTH, DELETE)
   - Messaging (SEND, GET, MARK_READ)
   - Status (GET_UNREAD_COUNT)
   - Error handling
"""

from enum import Enum, auto, IntEnum
import struct
from typing import Tuple, Optional

# Protocol version
PROTOCOL_VERSION = 0

class Command(IntEnum):
    """
    Command codes for the custom protocol.
    
    Each command represents a specific operation in the chat system.
    Using IntEnum ensures commands are serialized consistently as integers.
    
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
    
    Creates a message in the format:
    [version:1][command:1][length:2][payload:length]
    
    Args:
        command: The command to send (from Command enum)
        payload: Raw bytes of the payload
        
    Returns:
        bytes: The complete encoded message
        
    The header is packed using network byte order (big-endian)
    to ensure consistent transmission across different platforms.
    """
    length = len(payload)
    header = struct.pack('!BBH', PROTOCOL_VERSION, command.value, length)
    return header + payload

def decode_message(data: bytes) -> Tuple[Command, bytes]:
    """
    Decode a message according to the binary protocol.
    
    Extracts components from a message in the format:
    [version:1][command:1][length:2][payload:length]
    
    Args:
        data: The raw message data
        
    Returns:
        Tuple[Command, bytes]: The command and payload
        
    Raises:
        ValueError: If message format is invalid, version unsupported,
                   or command unknown
    """
    if len(data) < 4:  # Version (1) + Command (1) + Length (2)
        raise ValueError("Message too short")
        
    version, command_val, length = struct.unpack('!BBH', data[:4])
    if version != PROTOCOL_VERSION:
        raise ValueError(f"Unsupported protocol version: {version}")
    
    try:
        command = Command(command_val)
    except ValueError:
        raise ValueError(f"Invalid command value: {command_val}")
        
    if len(data) < 4 + length:
        raise ValueError("Incomplete message")
        
    payload = data[4:4+length]
    return command, payload 