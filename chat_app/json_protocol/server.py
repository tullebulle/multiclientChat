"""
JSON Protocol Server Implementation

Server implementation using the JSON protocol.
"""

import socketserver
import logging
from datetime import datetime
import fnmatch
from ..common.server_base import ThreadedTCPServer
from . import protocol

# Set up logging at the start of the file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class JSONChatRequestHandler(socketserver.BaseRequestHandler):
    """Handler for JSON protocol chat clients"""
    
    def setup(self):
        """Get reference to the shared chat server instance"""
        self.chat_server = self.server.chat_server
        self.current_user = None
    
    def handle(self):
        """Handle incoming client connection."""
        logging.info(f"New JSON client connection from {self.client_address}")
        
        while True:
            try:
                # Receive data from client
                data = self.request.recv(4096)  # Larger buffer for JSON
                if not data:
                    break
                    
                # Decode and handle the message
                try:
                    command, payload = protocol.decode_message(data)
                    self.handle_message(command, payload)
                except Exception as e:
                    logging.error(f"Failed to handle message: {e}")
                    error_response = {
                        'status': 'error',
                        'message': str(e)
                    }
                    self.send_response(protocol.Command.ERROR, error_response)
                    
            except Exception as e:
                logging.error(f"Error handling client: {e}")
                break
                
        logging.info(f"JSON client connection closed from {self.client_address}")
    
    def handle_message(self, command: str, payload: dict):
        """Handle a decoded message"""
        logging.debug(f"Handling message - Command: {command}, Payload: {payload}")
        
        try:
            if not self.current_user and command not in [
                protocol.Command.AUTH.name,
                protocol.Command.CREATE_ACCOUNT.name,
                protocol.Command.ERROR.name,
                protocol.Command.DELETE_ACCOUNT.name
            ]:
                response = {
                    'status': 'error',
                    'message': 'Not authenticated'
                }
                self.send_response(protocol.Command.ERROR, response)
                return
            
            if command == protocol.Command.AUTH.name:
                success = self.chat_server.authenticate(
                    payload['username'],
                    payload['password']
                )
                if success:
                    self.current_user = payload['username']
                response = {
                    'status': 'success' if success else 'error',
                    'message': 'Authentication successful' if success else 'Authentication failed'
                }
                    
            elif command == protocol.Command.CREATE_ACCOUNT.name:
                success = self.chat_server.create_account(
                    payload['username'],
                    payload['password']
                )
                response = {
                    'status': 'success' if success else 'error',
                    'message': 'Account created' if success else 'Username taken'
                }
                
            elif command == protocol.Command.LIST_ACCOUNTS.name:
                pattern = payload.get('pattern', '*')
                logging.debug(f"Listing accounts with pattern: {pattern}")
                
                # Get matching accounts - exactly like custom protocol
                accounts = list(self.chat_server.users.keys())
                logging.debug(f"All users in system: {accounts}")
                
                # Add debug for each pattern match attempt
                matching_accounts = []
                for username in accounts:
                    matches = fnmatch.fnmatch(username.lower(), pattern.lower())
                    logging.debug(f"Testing {username} against pattern {pattern}: {matches}")
                    if matches:
                        matching_accounts.append(username)
                
                logging.debug(f"Found {len(matching_accounts)} matching accounts: {matching_accounts}")
                response = {
                    'status': 'success',
                    'accounts': matching_accounts
                }
                logging.debug(f"Sending response: {response}")
                self.send_response(getattr(protocol.Command, command), response)
                return
                
            elif command == protocol.Command.SEND_MESSAGE.name:
                try:
                    message = self.chat_server.send_message(
                        self.current_user,
                        payload['recipient'],
                        payload['content']
                    )
                    response = {
                        'status': 'success',
                        'message_id': message.id
                    }
                except ValueError as e:
                    response = {
                        'status': 'error',
                        'message': str(e)
                    }
                    
            elif command == protocol.Command.GET_MESSAGES.name:
                try:
                    include_read = payload.get('include_read', True)
                    messages = self.chat_server.get_messages(
                        self.current_user,
                        include_read
                    )
                    response = {
                        'status': 'success',
                        'messages': [
                            {
                                'id': msg.id,
                                'sender': msg.sender,
                                'content': msg.content,
                                'timestamp': msg.timestamp.isoformat(),
                                'is_read': msg.is_read
                            }
                            for msg in messages
                        ]
                    }
                except ValueError as e:
                    response = {
                        'status': 'error',
                        'message': str(e)
                    }
                    
            elif command == protocol.Command.MARK_READ.name:
                try:
                    success = self.chat_server.mark_messages_read(
                        self.current_user,
                        payload['message_ids']
                    )
                    response = {
                        'status': 'success' if success else 'error'
                    }
                except ValueError as e:
                    response = {
                        'status': 'error',
                        'message': str(e)
                    }
                    
            elif command == protocol.Command.DELETE_MESSAGES.name:
                try:
                    success = self.chat_server.delete_messages(
                        self.current_user,
                        payload['message_ids']
                    )
                    response = {
                        'status': 'success' if success else 'error'
                    }
                except ValueError as e:
                    response = {
                        'status': 'error',
                        'message': str(e)
                    }
                    
            elif command == protocol.Command.DELETE_ACCOUNT.name:
                try:
                    success = self.chat_server.delete_account(
                        payload['username'],
                        payload['password']
                    )
                    response = {
                        'status': 'success' if success else 'error',
                        'message': 'Account deleted' if success else 'Failed to delete account'
                    }
                    if success and self.current_user == payload['username']:
                        self.current_user = None
                except ValueError as e:
                    response = {
                        'status': 'error',
                        'message': str(e)
                    }
            
            else:
                response = {
                    'status': 'error',
                    'message': 'Unknown command'
                }
                
            self.send_response(getattr(protocol.Command, command), response)
            
        except Exception as e:
            logging.error(f"Error handling message: {e}", exc_info=True)
            self.send_response(
                protocol.Command.ERROR,
                {'status': 'error', 'message': str(e)}
            )
    
    def send_response(self, command: protocol.Command, payload: dict):
        """Send a response to the client"""
        try:
            message = protocol.encode_message(command, payload)
            self.request.sendall(message)
        except Exception as e:
            logging.error(f"Error sending response: {e}")

class JSONChatServer(ThreadedTCPServer):
    """Chat server using JSON protocol"""
    def __init__(self, server_address):
        super().__init__(server_address, JSONChatRequestHandler) 

    def get_unread_count(self, username: str) -> dict:
        """Get count of unread messages for a user"""
        if username not in self.users:
            return {"status": "error", "message": "User not found"}
        
        count = sum(
            1 
            for msg in self.messages 
            if msg["recipient"] == username and not msg["read"]
        )
        
        return {
            "status": "success",
            "count": count
        } 