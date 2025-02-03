"""
Chat Application Protocol Definition

This module defines the custom wire protocol for the chat application.
It provides constants and utilities for message encoding/decoding.
"""

from enum import IntEnum
from typing import Tuple, Optional
import struct

class Command(IntEnum):
    """Command codes for the chat protocol"""
    AUTH = 0x01
    CREATE_ACCOUNT = 0x02
    SEND_MESSAGE = 0x03
    RECEIVE_MESSAGE = 0x04
    LIST_ACCOUNTS = 0x05
    DELETE_MESSAGE = 0x06
    DELETE_ACCOUNT = 0x07
    ERROR = 0x08

def encode_message(command: Command, payload: bytes) -> bytes:
    """
    Encode a message according to the protocol format.
    
    Args:
        command (Command): The command code
        payload (bytes): The message payload
        
    Returns:
        bytes: The encoded message
    """
    length = len(payload)
    return struct.pack('!BH', command, length) + payload

def decode_message(data: bytes) -> Tuple[Command, bytes]:
    """
    Decode a message according to the protocol format.
    
    Args:
        data (bytes): The raw message data
        
    Returns:
        Tuple[Command, bytes]: The command and payload
    """
    if len(data) < 3:  # Add size check
        raise ValueError("Message too short")
    command, length = struct.unpack('!BH', data[0:3])
    if len(data) < 3 + length:  # Add payload size check
        raise ValueError("Incomplete message")
    payload = data[3:3+length]
    return Command(command), payload 