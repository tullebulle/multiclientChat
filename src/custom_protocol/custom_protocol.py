"""
Custom Binary Protocol Implementation

Defines the binary protocol for the chat application.
"""

from enum import Enum, auto, IntEnum
import struct
from typing import Tuple, Optional, Dict
from ..common.commands import Command
import logging

# Protocol version
PROTOCOL_VERSION = 0

# Set up logging at the start of the file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def encode_message(command: Command, message: Dict) -> bytes:
    """
    Encode a message according to the binary protocol.
    Format: [version:1][command:1][length:2][payload:length]
    
    Args:
        command: The command to send
        payload: Raw bytes of the payload
        TODO: adapt
    Returns:
        The encoded message as bytes
    """
   
    # Formats:
    # CREATE ACCOUNT Format: [username_length][username][password_length][password]
    # AUTH Format: [username_length][username][password_length][password]
    # SEND_MESSAGE Format: [recipient_len][recipient][content_len:2][content]

    if command == Command.CREATE_ACCOUNT:
        # Format: [username_length][username][password_length][password]
        username = message["username"]
        password = message["password"]

        payload = bytes([len(username)]) + username.encode()
        payload += bytes([len(password)]) + password.encode()

        logging.debug(f"Create account payload: {[b for b in payload]}")
        logging.debug(f"Username: '{username}', length: {len(username)}")
        logging.debug(f"Password length: {len(password)}")
        logging.debug(f"Password hash: {hash(password)}")

    elif command == Command.AUTH:
        # Format: [username_length][username][password_length][password]
        username = message["username"]
        password = message["password"]

        payload = bytes([len(username)]) + username.encode()
        payload += bytes([len(password)]) + password.encode()

        logging.debug(f"Create account payload: {[b for b in payload]}")
        logging.debug(f"Username: '{username}', length: {len(username)}")
        logging.debug(f"Password length: {len(password)}")
        logging.debug(f"Password hash: {hash(password)}")

    elif command == Command.LIST_ACCOUNTS:
        # Format: [pattern_length][pattern]
        pattern = message["pattern"]

        payload = bytes([len(pattern)]) + pattern.encode()

        logging.debug(f"Listing accounts with pattern: '{pattern}'")

    elif command == Command.SEND_MESSAGE:
        # Format: [recipient_len][recipient][content_len:2][content]
        recipient = message["recipient"]
        content = message["content"]

        payload = bytes([len(recipient)]) + recipient.encode()
        payload += struct.pack('!H', len(content)) + content.encode()
        
        logging.debug(f"Sending message to {recipient}: {content}")

    elif command == Command.GET_MESSAGES:
        # Format: [include_read:1]
        include_read = message["include_read"]

        payload = bytes([int(include_read)])

    elif command == Command.MARK_READ:
        # Format: [count:2][id1:4][id2:4]...
        message_ids = message["message_ids"]

        payload = struct.pack('!H', len(message_ids))
        for msg_id in message_ids:
            payload += struct.pack('!I', msg_id)

    elif command == Command.DELETE_MESSAGES:
        # Format: [count:2][id1:4][id2:4]...
        message_ids = message["message_ids"]

        payload = struct.pack('!H', len(message_ids))
        for msg_id in message_ids:
            payload += struct.pack('!I', msg_id)

    elif command == Command.DELETE_ACCOUNT:
        # Format: [username_length][username][password_length][password]
        username = message["username"]
        password = message["password"]

        payload = bytes([len(username)]) + username.encode()
        payload += bytes([len(password)]) + password.encode()

        logging.debug(f"Attempting to delete account: {username}")

    elif command == Command.GET_UNREAD_COUNT:
        payload = bytes()
    
    else:
        raise ValueError("Command not found.")

    length = len(payload)
    header = struct.pack('!BBH', PROTOCOL_VERSION, command.value, length)
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
    # Checking the Header
    if len(data) < 4:  # Version (1) + Command (1) + Length (2)
        raise ValueError("Message too short")
        
    version, command_val, length = struct.unpack('!BBH', data[:4])
    if version != PROTOCOL_VERSION: # Checking if the version is supported
        raise ValueError(f"Unsupported protocol version: {version}")
    
    try:
        command = Command(command_val)
    except ValueError:
        raise ValueError(f"Invalid command value: {command_val}")
        
    if len(data) != 4 + length:
        raise ValueError("Incomplete message")
        
    payload = data[4:4+length]

    # Decoding the payload

    if command == Command.CREATE_ACCOUNT:
        if (payload == b'\x01'):
            print("Account created successfully!")
            message = {}
        else:
            print("Failed to create account: Username might be taken")
            
        return success

    elif command == Command.AUTH:
        success = (payload == b'\x01')
        if success:
            print("Account created successfully!")
        else:
            print("Failed to create account: Username might be taken")
        return success

    elif command == Command.LIST_ACCOUNTS:
        # Format: [pattern_length][pattern]
        pattern = message["pattern"]

        payload = bytes([len(pattern)]) + pattern.encode()

        logging.debug(f"Listing accounts with pattern: '{pattern}'")

    elif command == Command.SEND_MESSAGE:
        # Format: [recipient_len][recipient][content_len:2][content]
        recipient = message["recipient"]
        content = message["content"]

        payload = bytes([len(recipient)]) + recipient.encode()
        payload += struct.pack('!H', len(content)) + content.encode()
        
        logging.debug(f"Sending message to {recipient}: {content}")

    elif command == Command.GET_MESSAGES:
        # Format: [include_read:1]
        include_read = message["include_read"]

        payload = bytes([int(include_read)])

    elif command == Command.MARK_READ:
        # Format: [count:2][id1:4][id2:4]...
        message_ids = message["message_ids"]

        payload = struct.pack('!H', len(message_ids))
        for msg_id in message_ids:
            payload += struct.pack('!I', msg_id)

    elif command == Command.DELETE_MESSAGES:
        # Format: [count:2][id1:4][id2:4]...
        message_ids = message["message_ids"]

        payload = struct.pack('!H', len(message_ids))
        for msg_id in message_ids:
            payload += struct.pack('!I', msg_id)

    elif command == Command.DELETE_ACCOUNT:
        # Format: [username_length][username][password_length][password]
        username = message["username"]
        password = message["password"]

        payload = bytes([len(username)]) + username.encode()
        payload += bytes([len(password)]) + password.encode()

        logging.debug(f"Attempting to delete account: {username}")

    elif command == Command.GET_UNREAD_COUNT:
        payload = bytes()
    
    else:
        raise ValueError("Command not found.")

    return command, message 