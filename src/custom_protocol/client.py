"""
Custom Protocol Chat Client

A command-line client using the custom binary protocol.
"""

import socket
import argparse
import getpass
import sys
import logging
import struct
from datetime import datetime
from src.custom_protocol import protocol

# Set up logging at the start of the file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class CustomChatClient:
    """Interactive chat client using custom binary protocol"""
    
    def __init__(self, host='localhost', port=9999):
        """Initialize the chat client"""
        self.host = host
        self.port = port
        self.sock = None
        self.current_user = None
        logging.debug(f"Initialized client for {host}:{port}")
        
    def connect(self, server_address=None):
        """Connect to the chat server
        
        Args:
            server_address: Optional tuple of (host, port). If not provided, uses defaults.
        """
        if server_address:
            self.host, self.port = server_address
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            return True
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            return False
            
    def disconnect(self):
        """Close the connection"""
        self.sock.close()
            
    def send_command(self, command: protocol.Command, payload: bytes) -> tuple:
        """Send a command to the server and get the response"""
        if not self.sock:
            logging.error("Not connected to server")
            return None
            
        try:
            # Send command
            message = protocol.encode_message(command, payload)
            logging.debug(f"Sending command {command.name} with payload length {len(payload)}")
            logging.debug(f"Raw payload bytes: {[b for b in payload]}")
            self.sock.sendall(message)
            
            # Get response
            response = self.sock.recv(1024)
            cmd, payload = protocol.decode_message(response)
            logging.debug(f"Received response: command={cmd.name}, payload={[b for b in payload]}")
            return cmd, payload
        except Exception as e:
            logging.error(f"Error sending command: {e}")
            return None
            
    def create_account(self, username=None, password=None):
        """Create a new account"""
        if username is None:
            username = input("Username: ").strip()
        if password is None:
            password = getpass.getpass("Password: ").strip()
        
        # Format: [username_length][username][password_length][password]
        payload = bytes([len(username)]) + username.encode()
        payload += bytes([len(password)]) + password.encode()
        
        logging.debug(f"Create account payload: {[b for b in payload]}")
        logging.debug(f"Username: '{username}', length: {len(username)}")
        logging.debug(f"Password length: {len(password)}")
        logging.debug(f"Password hash: {hash(password)}")
        
        response = self.send_command(protocol.Command.CREATE_ACCOUNT, payload)
        if response:
            _, result = response
            logging.debug(f"Create account response: {[b for b in result]}")
            success = result == b'\x01'
            if success:
                print("Account created successfully!")
            else:
                print("Failed to create account: Username might be taken")
            return success, None
                
    def login(self, username=None, password=None):
        """Log in to an existing account"""
        if username is None:
            username = input("Username: ").strip()
        if password is None:
            password = getpass.getpass("Password: ").strip()
        
        # Format: [username_length][username][password_length][password]
        payload = bytes([len(username)]) + username.encode()
        payload += bytes([len(password)]) + password.encode()
        
        logging.debug(f"Login payload: {[b for b in payload]}")
        logging.debug(f"Username: '{username}', length: {len(username)}")
        logging.debug(f"Password length: {len(password)}")
        logging.debug(f"Password hash: {hash(password)}")
        
        response = self.send_command(protocol.Command.AUTH, payload)
        if response:
            _, result = response
            logging.debug(f"Auth response: {[b for b in result]}")
            success = result == b'\x01'
            if success:
                self.current_user = username
                print("Logged in successfully!")
            else:
                print("Login failed!")
            return success
                
    def list_accounts(self, pattern=None):
        """List accounts matching a pattern"""
        if pattern is None:
            pattern = input("Search pattern (or press Enter for all): ").strip() or "*"
        
        # Format: [pattern_length][pattern]
        payload = bytes([len(pattern)]) + pattern.encode()
        
        logging.debug(f"Listing accounts with pattern: '{pattern}'")
        response = self.send_command(protocol.Command.LIST_ACCOUNTS, payload)
        logging.debug(f"List accounts response: {response}")
        if response:
            cmd, result = response
            if cmd == protocol.Command.ERROR:
                print(f"Error listing accounts: {result.decode()}")
                return None
            
            try:
                # Parse response: [num_accounts][len1][name1][len2][name2]...
                num_accounts = result[0]
                logging.debug(f"Number of accounts: {num_accounts}")
                pos = 1
                accounts = []
                
                for _ in range(num_accounts):
                    name_len = result[pos]
                    logging.debug(f"Name length: {name_len}")
                    name = result[pos+1:pos+1+name_len].decode('utf-8')
                    logging.debug(f"Name: {name}")
                    accounts.append(name)
                    pos += 1 + name_len
                
                return accounts
                
            except Exception as e:
                logging.error(f"Error parsing list_accounts response: {e}")
                return None

    def send_message(self, recipient: str, content: str) -> bool:
        """
        Send a message to another user
        
        Args:
            recipient: Username of recipient
            content: Message content
            
        Returns:
            bool: True if message sent successfully
        """
        if not self.current_user:
            logging.error("Not logged in")
            return False
        
        # Format: [recipient_len][recipient][content_len:2][content]
        payload = bytes([len(recipient)]) + recipient.encode()
        payload += struct.pack('!H', len(content)) + content.encode()
        
        logging.debug(f"Sending message to {recipient}: {content}")
        response = self.send_command(protocol.Command.SEND_MESSAGE, payload)
        
        if response:
            cmd, result = response
            if cmd == protocol.Command.ERROR:
                logging.error(f"Failed to send message: {result.decode()}")
                return False
            else:
                message_id = struct.unpack('!I', result[:4])[0]
                logging.debug(f"Message sent successfully (ID: {message_id})")
                return True
        return False

    def get_messages(self, include_read=True) -> list:
        """
        Get messages for the current user
        
        Args:
            include_read: Whether to include previously read messages
            
        Returns:
            list: List of message dictionaries
        """
        if not self.current_user:
            logging.error("Not logged in")
            return []
        
        # Format: [include_read:1]
        payload = bytes([int(include_read)])
        
        response = self.send_command(protocol.Command.GET_MESSAGES, payload)
        if response:
            cmd, result = response
            if cmd == protocol.Command.ERROR:
                logging.error(f"Failed to get messages: {result.decode()}")
                return []
            
            # Parse response: [count:2][id:4][sender_len:1][sender:N][content_len:2][content:M][timestamp:8][is_read:1]...
            messages = []
            try:
                count = struct.unpack('!H', result[:2])[0]
                pos = 2
                
                for _ in range(count):
                    msg_id = struct.unpack('!I', result[pos:pos+4])[0]
                    pos += 4
                    
                    sender_len = result[pos]
                    pos += 1
                    sender = result[pos:pos+sender_len].decode()
                    pos += sender_len
                    
                    content_len = struct.unpack('!H', result[pos:pos+2])[0]
                    pos += 2
                    content = result[pos:pos+content_len].decode()
                    pos += content_len
                    
                    timestamp = struct.unpack('!Q', result[pos:pos+8])[0]
                    pos += 8
                    
                    is_read = bool(result[pos])
                    pos += 1
                    
                    messages.append({
                        'id': msg_id,
                        'sender': sender,
                        'content': content,
                        'timestamp': datetime.fromtimestamp(timestamp),
                        'is_read': is_read
                    })
                
                return messages
                
            except Exception as e:
                logging.error(f"Error parsing messages: {e}")
                return []
        
        return []

    def mark_read(self, message_ids: list) -> bool:
        """
        Mark messages as read
        
        Args:
            message_ids: List of message IDs to mark as read
            
        Returns:
            bool: True if successful
        """
        if not self.current_user:
            logging.error("Not logged in")
            return False
        
        # Format: [count:2][id1:4][id2:4]...
        payload = struct.pack('!H', len(message_ids))
        for msg_id in message_ids:
            payload += struct.pack('!I', msg_id)
        
        response = self.send_command(protocol.Command.MARK_READ, payload)
        if response:
            cmd, result = response
            if cmd == protocol.Command.ERROR:
                logging.error(f"Failed to mark messages as read: {result.decode()}")
                return False
            return True
        return False

    def delete_messages(self, message_ids: list) -> bool:
        """
        Delete specific messages
        
        Args:
            message_ids: List of message IDs to delete
            
        Returns:
            bool: True if successful
        """
        if not self.current_user:
            logging.error("Not logged in")
            return False
        
        # Format: [count:2][id1:4][id2:4]...
        payload = struct.pack('!H', len(message_ids))
        for msg_id in message_ids:
            payload += struct.pack('!I', msg_id)
        
        response = self.send_command(protocol.Command.DELETE_MESSAGES, payload)
        if response:
            cmd, result = response
            if cmd == protocol.Command.ERROR:
                logging.error(f"Failed to delete messages: {result.decode()}")
                return False
            return True
        return False

    def delete_account(self, username: str, password: str) -> bool:
        """
        Delete a user account
        
        Args:
            username: Username of account to delete
            password: Password for verification
            
        Returns:
            bool: True if account was deleted successfully
        """
        # Format: [username_length][username][password_length][password]
        payload = bytes([len(username)]) + username.encode()
        payload += bytes([len(password)]) + password.encode()
        
        logging.debug(f"Attempting to delete account: {username}")
        response = self.send_command(protocol.Command.DELETE_ACCOUNT, payload)
        
        if response:
            cmd, result = response
            if cmd == protocol.Command.ERROR:
                logging.error(f"Failed to delete account: {result.decode()}")
                return False
            success = result == b'\x01'
            if success:
                logging.info(f"Account deleted successfully: {username}")
            return success
        return False

    def get_unread_count(self) -> int:
        """
        Get count of unread messages for current user
        
        Returns:
            int: Number of unread messages, or -1 if error
        """
        if not self.current_user:
            logging.error("Not logged in")
            return -1
        
        response = self.send_command(protocol.Command.GET_UNREAD_COUNT, b'')
        if response:
            cmd, result = response
            if cmd == protocol.Command.ERROR:
                logging.error(f"Failed to get unread count: {result.decode()}")
                return -1
            return struct.unpack('!H', result)[0]
        return -1

    def main_loop(self):
        """Main client loop"""
        commands = {
            "1": ("Create account", self.create_account),
            "2": ("Login", self.login),
            "3": ("List accounts", self.list_accounts),
            "4": ("Send message", self.send_message),
            "5": ("Get messages", self.get_messages),
            "6": ("Mark messages as read", self.mark_read),
            "7": ("Delete messages", self.delete_messages),
            "8": ("Delete account", self.delete_account),
            "9": ("Get unread count", self.get_unread_count),
            "10": ("Quit", lambda: "quit")
        }
        
        while True:
            print("\nAvailable commands:")
            for key, (name, _) in commands.items():
                print(f"{key}: {name}")
            if self.current_user:
                print(f"\nLogged in as: {self.current_user}")
            else:
                print("\nNot logged in")
                
            choice = input("\nEnter command number: ").strip()
            
            if choice not in commands:
                print("Invalid command!")
                continue
                
            name, func = commands[choice]
            result = func()
            
            if result == "quit":
                break

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Chat client (Custom Protocol)")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=9999, help="Server port")
    args = parser.parse_args()
    
    client = CustomChatClient(args.host, args.port)
    if client.connect():
        try:
            client.main_loop()
        finally:
            client.disconnect()

if __name__ == "__main__":
    main() 