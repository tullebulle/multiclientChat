"""
JSON Protocol Server Implementation

This module implements the server-side handling of the JSON protocol. It provides
a full-featured chat server using JSON messages for human-readable communication.

Key Components:
1. Request Handler:
   - Processes individual client connections
   - Parses JSON messages
   - Manages user sessions
   - Handles command execution

2. Server Class:
   - Manages multiple client connections
   - Inherits from ThreadedTCPServer
   - Maintains shared state

Protocol Features:
- JSON message format for readability
- Maximum message size of 65539 bytes
- Full command support
- Descriptive error messages
- Session-based authentication
"""

import socketserver
import logging
from datetime import datetime
import fnmatch
from ..common.server_base import ThreadedTCPServer
from . import protocol

# Set up logging with simpler format
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

class JSONChatRequestHandler(socketserver.BaseRequestHandler):
    """
    Handler for JSON protocol chat clients.
    
    This class processes individual client connections using the JSON protocol.
    It handles message parsing, command execution, and maintains client state
    throughout the connection lifetime.
    
    Attributes:
        chat_server: Reference to the shared chat server instance
        current_user: Currently authenticated username (or None)
        request: Client socket connection
        
    The handler maintains session state and enforces authentication
    requirements for protected commands.
    """
    
    def setup(self):
        """
        Initialize the request handler.
        
        Called when a new client connects. Sets up the handler's initial state
        and gets a reference to the shared chat server instance.
        """
        self.chat_server = self.server.chat_server
        self.current_user = None
    
    def handle(self):
        """
        Handle incoming client connection.
        
        Main processing loop for client connections. Continuously receives
        and processes JSON messages until the connection is closed.
        
        Message Flow:
        1. Receive raw data (up to max message size)
        2. Parse JSON message
        3. Validate protocol format
        4. Process command
        5. Send JSON response
        
        Authentication is required for all commands except CREATE_ACCOUNT
        and AUTH. Messages exceeding the size limit are rejected.
        """
        while True:
            try:
                # Maximum message size for JSON protocol
                # Using same size as custom protocol for consistency
                max_message_size = 65539  # 4 byte header + 65535 byte payload
                data = self.request.recv(max_message_size)
                if not data:
                    break
                    
                command, payload = protocol.decode_message(data)
                logging.debug(f"Received {command} command")
                
                # Commands that don't require authentication
                if command == protocol.Command.CREATE_ACCOUNT:
                    try:
                        username = payload['username']
                        password = payload['password']
                        
                        success = self.chat_server.create_account(username, password)
                        if success:
                            response = {'status': 'success'}
                        else:
                            response = {'status': 'error', 'message': 'Username already exists'}
                            
                        self.send_response(command, response)
                    except Exception as e:
                        self.send_error(str(e))
                    continue
                    
                elif command == protocol.Command.AUTH:
                    try:
                        username = payload['username']
                        password = payload.get('password') or payload.get('password_hash')
                        success = self.chat_server.authenticate(username, password)
                        if success:
                            self.current_user = username
                        response = {'status': 'success' if success else 'error'}
                        self.send_response(command, response)
                    except Exception as e:
                        self.send_error(str(e))
                    continue
                    
                # All other commands require authentication
                if not self.current_user:
                    self.send_error("Not authenticated")
                    continue
                    
                # Handle authenticated commands...
                self.handle_message(command, payload)
                
            except Exception as e:
                logging.error(f"Connection error: {e}")
                break
                
        logging.debug("Client connection closed")
    
    def handle_message(self, command: protocol.Command, payload: dict):
        """Handle a decoded message"""
        try:
            if command == protocol.Command.GET_MESSAGES:
                try:
                    include_read = payload.get('include_read', True)
                    username = payload.get('username', self.current_user)
                    
                    messages = self.chat_server.get_messages(username, include_read)
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
                    self.send_response(command, response)
                except Exception as e:
                    self.send_error(str(e))
                return
                
            elif command == protocol.Command.LIST_ACCOUNTS:
                try:
                    pattern = payload.get('pattern', '*')
                    page = payload.get('page', 1)
                    page_size = payload.get('page_size', 10)
                    
                    accounts = list(self.chat_server.users.keys())
                    matching_accounts = [
                        username for username in accounts 
                        if fnmatch.fnmatch(username.lower(), pattern.lower())
                    ]
                    matching_accounts.sort()
                    
                    total_accounts = len(matching_accounts)
                    total_pages = (total_accounts + page_size - 1) // page_size
                    
                    start_idx = (page - 1) * page_size
                    end_idx = start_idx + page_size
                    paginated_accounts = matching_accounts[start_idx:end_idx]
                    
                    response = {
                        'status': 'success',
                        'accounts': paginated_accounts,
                        'total_pages': total_pages,
                        'total_accounts': total_accounts
                    }
                    self.send_response(command, response)
                except Exception as e:
                    self.send_error(str(e))
                return
                
            elif command == protocol.Command.SEND_MESSAGE:
                try:
                    recipient = payload['recipient']
                    content = payload['content']
                    
                    message = self.chat_server.send_message(
                        self.current_user,
                        recipient,
                        content
                    )
                    
                    response = {
                        'status': 'success',
                        'message_id': message.id,
                        'timestamp': message.timestamp.isoformat()
                    }
                    self.send_response(command, response)
                except Exception as e:
                    self.send_error(str(e))
                return
                
            elif command == protocol.Command.MARK_READ:
                try:
                    marked = self.chat_server.mark_messages_read(
                        self.current_user,
                        payload['message_ids']
                    )
                    response = {'status': 'success', 'marked_count': marked}
                    self.send_response(command, response)
                except Exception as e:
                    self.send_error(str(e))
                return
                
            elif command == protocol.Command.DELETE_MESSAGES:
                try:
                    deleted = self.chat_server.delete_messages(
                        self.current_user,
                        payload['message_ids']
                    )
                    response = {'status': 'success', 'deleted_count': deleted}
                    self.send_response(command, response)
                except Exception as e:
                    self.send_error(str(e))
                return
                
            elif command == protocol.Command.DELETE_ACCOUNT:
                try:
                    success = self.chat_server.delete_account(
                        payload['username'],
                        payload['password']
                    )
                    if success and payload['username'] == self.current_user:
                        self.current_user = None
                    response = {'status': 'success' if success else 'error'}
                    self.send_response(command, response)
                except Exception as e:
                    self.send_error(str(e))
                return
                
            elif command == protocol.Command.GET_UNREAD_COUNT:
                try:
                    messages = self.chat_server.get_messages(
                        self.current_user,
                        include_read=False
                    )
                    response = {
                        'status': 'success',
                        'count': len(messages)
                    }
                    self.send_response(command, response)
                except Exception as e:
                    self.send_error(str(e))
                return
            
            else:
                self.send_error("Command not implemented")
                return
                
        except Exception as e:
            logging.error(f"Error handling {command}: {e}")
            self.send_error(str(e))
    
    def send_response(self, command: protocol.Command, payload: dict):
        """Send a response to the client"""
        try:
            message = protocol.encode_message(command, payload)
            self.request.sendall(message)
        except Exception as e:
            logging.error(f"Error sending response: {e}")

    def send_error(self, error_message: str):
        """Send an error response to the client"""
        try:
            response = {'status': 'error', 'message': error_message}
            self.send_response(protocol.Command.ERROR, response)
        except Exception as e:
            logging.error(f"Error sending error response: {e}")

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