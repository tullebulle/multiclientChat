"""
Custom Protocol Server Implementation

Server implementation using the custom binary protocol.
"""

import socketserver
import logging
from src.common.server_base import ThreadedTCPServer
from . import protocol
import struct
from datetime import datetime
import fnmatch

class CustomChatRequestHandler(socketserver.BaseRequestHandler):
    """Handler for custom protocol chat clients"""
    
    def setup(self):
        """Get reference to the shared chat server instance"""
        self.chat_server = self.server.chat_server
        self.current_user = None
    
    def handle(self):
        """Handle incoming client connection."""
        logging.info(f"New custom protocol client connection from {self.client_address}")
        
        while True:
            try:
                # Receive data from client
                logging.debug("Waiting for client data...")
                data = self.request.recv(1024) # need to modify this to receive larger messages
                if not data:
                    logging.info("Client closed connection")
                    break
                    
                # Decode and handle the message
                try:
                    logging.debug(f"Received raw data: {data}")
                    command, payload = protocol.decode_message(data)
                    logging.debug(f"Decoded command: {command}, payload: {payload}")
                    self.handle_message(command, payload)
                except Exception as e:
                    logging.error(f"Failed to handle message: {e}", exc_info=True)
                    error_msg = str(e).encode('utf-8')
                    self.send_response(protocol.Command.ERROR, error_msg)
                    
            except Exception as e:
                logging.error(f"Error handling client: {e}", exc_info=True)
                break
                
        logging.info(f"Custom protocol client connection closed from {self.client_address}")
    
    def handle_message(self, command: protocol.Command, payload: bytes):
        """Handle a decoded message"""
        try:
            logging.debug(f"Handling command: {command} with payload: {payload}")
            
            if not self.current_user and command not in [
                protocol.Command.AUTH,
                protocol.Command.CREATE_ACCOUNT,
                protocol.Command.ERROR
            ]:
                logging.debug("Rejecting unauthenticated command")
                self.send_error("Not authenticated")
                return
            
            if command == protocol.Command.CREATE_ACCOUNT:
                # Format: [username_len:1][username:N][password_len:1][password:M]
                username_len = payload[0]
                username = payload[1:username_len+1].decode('utf-8')
                password_len = payload[username_len+1]
                password = payload[username_len+2:username_len+2+password_len].decode('utf-8')
                
                logging.debug(f"Create account attempt for username: {username}")
                
                success = self.chat_server.create_account(username, password)
                response = b'\x01' if success else b'\x00'
                self.send_response(command, response)
                
            elif command == protocol.Command.AUTH:
                # Format: [username_len:1][username:N][password_len:1][password:M]
                username_len = payload[0]
                username = payload[1:username_len+1].decode('utf-8')
                password_len = payload[username_len+1]
                password = payload[username_len+2:username_len+2+password_len].decode('utf-8')
                
                logging.debug(f"Auth attempt for username: {username}")
                
                success = self.chat_server.authenticate(username, password)
                if success:
                    self.current_user = username
                    logging.debug(f"Authentication successful for {username}")
                else:
                    logging.debug(f"Authentication failed for {username}")
                
                response = b'\x01' if success else b'\x00'
                self.send_response(command, response)
                
            elif command == protocol.Command.LIST_ACCOUNTS:
                try:
                    # Format: [pattern_len:1][pattern:N]
                    pattern_len = payload[0]
                    pattern = payload[1:pattern_len+1].decode('utf-8')
                    
                    logging.info(f"Listing accounts with pattern: {pattern}")
                    
                    # Get matching accounts using fnmatch for wildcard support
                    accounts = list(self.chat_server.users.keys())
                    logging.info(f"Accounts: {accounts}")
                    matching_accounts = [
                        username for username in accounts 
                        if fnmatch.fnmatch(username.lower(), pattern.lower())
                    ]
                    logging.info(f"Matching accounts: {matching_accounts}")
                    
                    # Format response: [num_accounts:1][len1:1][name1:N][len2:1][name2:N]...
                    response = bytes([len(matching_accounts)])
                    for username in matching_accounts:
                        name_bytes = username.encode('utf-8')
                        response += bytes([len(name_bytes)]) + name_bytes
                    
                    logging.debug(f"Found {len(matching_accounts)} matching accounts")
                    self.send_response(command, response)
                    
                except Exception as e:
                    logging.error(f"Error listing accounts: {e}")
                    self.send_error(str(e))
                
            elif command == protocol.Command.SEND_MESSAGE:
                try:
                    # Format: [recipient_len:1][recipient:N][content_len:2][content:M]
                    recipient_len = payload[0]
                    recipient = payload[1:recipient_len+1].decode('utf-8')
                    content_len = struct.unpack('!H', payload[recipient_len+1:recipient_len+3])[0]
                    content = payload[recipient_len+3:recipient_len+3+content_len].decode('utf-8')
                    
                    logging.debug(f"Send message attempt from {self.current_user} to {recipient}")
                    
                    if not self.current_user:
                        raise ValueError("Not authenticated")
                        
                    if recipient not in self.chat_server.users:
                        raise ValueError(f"Recipient {recipient} does not exist")
                        
                    message = self.chat_server.send_message(
                        self.current_user,
                        recipient,
                        content
                    )
                    
                    # Response: [message_id:4]
                    response = struct.pack('!I', message.id)
                    self.send_response(command, response)
                    
                except ValueError as e:
                    logging.error(f"Error sending message: {e}")
                    self.send_error(str(e))
                    
            elif command == protocol.Command.GET_MESSAGES:
                try:
                    # Format: [include_read:1]
                    if len(payload) != 1:
                        raise ValueError("Invalid payload")
                        
                    include_read = bool(payload[0])
                    logging.debug(f"Getting messages for {self.current_user}, include_read={include_read}")
                    
                    messages = self.chat_server.get_messages(
                        self.current_user,
                        include_read
                    )
                    
                    logging.debug(f"Found {len(messages)} messages")
                    
                    # Response: [count:2][message_data...]
                    # message_data: [id:4][sender_len:1][sender:len][content_len:2][content:len][timestamp:8][is_read:1]
                    response = bytearray(struct.pack('!H', len(messages)))
                    
                    for msg in messages:
                        logging.debug(f"Adding message: id={msg.id}, sender={msg.sender}, content={msg.content}")
                        sender_bytes = msg.sender.encode('utf-8')
                        content_bytes = msg.content.encode('utf-8')
                        
                        response.extend(struct.pack('!I', msg.id))
                        response.append(len(sender_bytes))
                        response.extend(sender_bytes)
                        response.extend(struct.pack('!H', len(content_bytes)))
                        response.extend(content_bytes)
                        response.extend(struct.pack('!Q', int(msg.timestamp.timestamp())))
                        response.append(int(msg.is_read))
                    
                    logging.debug(f"Sending response with {len(response)} bytes")
                    self.send_response(command, response)
                    
                except ValueError as e:
                    self.send_error(str(e))
                    
            elif command == protocol.Command.MARK_READ:
                try:
                    # Format: [count:2][id1:4][id2:4]...
                    if len(payload) < 2:
                        raise ValueError("Invalid payload")
                        
                    count = struct.unpack('!H', payload[:2])[0]
                    if len(payload) != 2 + count * 4:
                        raise ValueError("Invalid message IDs")
                        
                    message_ids = []
                    for i in range(count):
                        msg_id = struct.unpack('!I', payload[2+i*4:6+i*4])[0]
                        message_ids.append(msg_id)
                    
                    marked = self.chat_server.mark_messages_read(
                        self.current_user,
                        message_ids
                    )
                    
                    # Response: [count:2]
                    response = struct.pack('!H', marked)
                    self.send_response(command, response)
                    
                except ValueError as e:
                    self.send_error(str(e))
                    
            elif command == protocol.Command.DELETE_MESSAGES:
                try:
                    # Format: [count:2][id1:4][id2:4]...
                    if len(payload) < 2:
                        raise ValueError("Invalid payload")
                        
                    count = struct.unpack('!H', payload[:2])[0]
                    logging.debug(f"Delete request for {count} messages from user {self.current_user}")
                    
                    if len(payload) != 2 + count * 4:
                        raise ValueError("Invalid message IDs")
                        
                    message_ids = []
                    for i in range(count):
                        msg_id = struct.unpack('!I', payload[2+i*4:6+i*4])[0]
                        message_ids.append(msg_id)
                    
                    logging.debug(f"Attempting to delete messages with IDs: {message_ids}")
                    logging.debug(f"Current messages in server: {self.chat_server.messages}")
                    
                    deleted = self.chat_server.delete_messages(
                        self.current_user,
                        message_ids
                    )
                    
                    logging.debug(f"Delete operation returned: {deleted}")
                    
                    # Response: [count:2]
                    response = struct.pack('!H', deleted)
                    self.send_response(command, response)
                    
                except ValueError as e:
                    logging.error(f"Error in delete_messages: {e}")
                    self.send_error(str(e))
            
            elif command == protocol.Command.DELETE_ACCOUNT:
                try:
                    # Format: [username_len:1][username:N][password_len:1][password:M]
                    username_len = payload[0]
                    username = payload[1:username_len+1].decode('utf-8')
                    password_len = payload[username_len+1]
                    password = payload[username_len+2:username_len+2+password_len].decode('utf-8')
                    
                    logging.debug(f"Delete account attempt for username: {username}")
                    
                    success = self.chat_server.delete_account(username, password)
                    response = b'\x01' if success else b'\x00'
                    self.send_response(command, response)
                    
                    if success and username == self.current_user:
                        self.current_user = None
                        
                except Exception as e:
                    logging.error(f"Error deleting account: {e}")
                    self.send_error(str(e))
            
            elif command == protocol.Command.GET_UNREAD_COUNT:
                try:
                    if not self.current_user:
                        raise ValueError("Not authenticated")
                    
                    # Get unread messages for current user
                    messages = self.chat_server.get_messages(
                        self.current_user,
                        include_read=False
                    )
                    
                    # Response: [count:2]
                    count = len(messages)
                    response = struct.pack('!H', count)
                    self.send_response(command, response)
                    
                except ValueError as e:
                    logging.error(f"Error getting unread count: {e}")
                    self.send_error(str(e))
            
            else:
                self.send_error("Command not implemented")
                
        except Exception as e:
            logging.error(f"Error handling message: {e}")
            self.send_error(str(e))
    
    def send_response(self, command: protocol.Command, payload: bytes):
        """Send a response to the client"""
        try:
            message = protocol.encode_message(command, payload)
            self.request.sendall(message)
        except Exception as e:
            logging.error(f"Error sending response: {e}")

    def send_error(self, error_message: str):
        """Send an error response to the client"""
        try:
            error_msg = error_message.encode('utf-8')
            self.send_response(protocol.Command.ERROR, error_msg)
        except Exception as e:
            logging.error(f"Error sending error response: {e}")

class CustomChatServer(ThreadedTCPServer):
    """Chat server using custom protocol"""
    def __init__(self, server_address):
        super().__init__(server_address, CustomChatRequestHandler) 