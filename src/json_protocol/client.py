"""
JSON Protocol Chat Client

A command-line client using the JSON protocol.
"""

import socket
import argparse
import getpass
import sys
import logging
import json
from typing import Tuple, Dict, Any
from . import json_protocol

class JSONChatClient:
    """Interactive chat client using JSON protocol"""
    
    def __init__(self, host: str = 'localhost', port: int = 9998):
        """Initialize the chat client"""
        self.host = host
        self.port = port
        self.sock = None
        self.current_user = None
        
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
        """Disconnect from the server"""
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
            self.current_user = None
            
    def send_command(self, command: json_protocol.Command, payload: dict) -> tuple:
        """Send a command to the server and get the response"""
        if not self.sock:
            logging.error("Not connected to server")
            return None
            
        try:
            # Send command
            message = json_protocol.encode_message(command, payload)
            self.sock.sendall(message)
            
            # Get response
            response = self.sock.recv(4096)  # Larger buffer for JSON
            if not response:
                raise ConnectionError("Server closed connection")
            return self.decode_response(response)
        except Exception as e:
            logging.error(f"Error sending command: {e}")
            return None

    def decode_response(self, data: bytes) -> Tuple[str, Dict[str, Any]]:
        """Decode a response from the server"""
        try:
            message = json.loads(data.decode('utf-8'))
            
            if "version" not in message:
                raise ValueError("Missing protocol version")
            if message["version"] != json_protocol.PROTOCOL_VERSION:
                raise ValueError(f"Unsupported protocol version: {message['version']}")
            
            if "command" not in message:
                raise ValueError("Message missing 'command' field")
            
            if "payload" not in message:
                raise ValueError("Message missing 'payload' field")
            
            # Convert Command enum to string name for test compatibility
            command = message["command"]
            if isinstance(command, json_protocol.Command):
                command = command.name
            elif isinstance(command, str) and hasattr(json_protocol.Command, command):
                # Already a string name, leave it as is
                pass
            else:
                raise ValueError(f"Invalid command: {command}")
            
            return command, message["payload"]
        
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")

    def send_message(self, recipient: str, content: str) -> int:
        """Send a message to another user
        
        Args:
            recipient: Username of the recipient
            content: Message content
            
        Returns:
            int: Message ID if successful, None on error
        """
        payload = {
            "recipient": recipient,
            "content": content
        }
        
        response = self.send_command(json_protocol.Command.SEND_MESSAGE, payload)
        if response:
            cmd, payload = response
            if payload.get("status") == "success":
                return payload.get("message_id")
        return None

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Chat client (JSON Protocol)")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=9998, help="Server port")
    args = parser.parse_args()
    
    client = JSONChatClient(args.host, args.port)
    if client.connect():
        try:
            client.main_loop()
        finally:
            client.disconnect()

if __name__ == "__main__":
    main() 