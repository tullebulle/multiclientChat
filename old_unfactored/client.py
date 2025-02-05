"""
Chat Client Application

A command-line client for interacting with the chat server.
Supports both JSON and custom binary protocols.
"""

import socket
import json
import json_protocol
import protocol
import argparse
import getpass
import sys
from typing import Optional, Tuple

class ChatClient:
    """Interactive chat client"""
    
    def __init__(self, host: str = 'localhost', port: int = 9999):
        """Initialize the chat client"""
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.current_user: Optional[str] = None
        
    def connect(self) -> bool:
        """Connect to the chat server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"Connected to server at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from the server"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            self.current_user = None
            
    def send_command(self, command: json_protocol.Command, payload: dict) -> Optional[Tuple[str, dict]]:
        """Send a command to the server and get the response"""
        if not self.socket:
            print("Not connected to server")
            return None
            
        try:
            # Send command
            message = json_protocol.encode_message(command, payload)
            self.socket.sendall(message)
            
            # Get response
            response = self.socket.recv(1024)
            command, payload = json_protocol.decode_message(response)
            return command, payload
        except Exception as e:
            print(f"Error sending command: {e}")
            return None
            
    def create_account(self):
        """Create a new account"""
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        
        response = self.send_command(
            json_protocol.Command.CREATE_ACCOUNT,
            {"username": username, "password": password}
        )
        
        if response:
            _, payload = response
            if payload["status"] == "success":
                print("Account created successfully!")
            else:
                print(f"Failed to create account: {payload['message']}")
                
    def login(self):
        """Log in to an existing account"""
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        
        response = self.send_command(
            json_protocol.Command.AUTH,
            {"username": username, "password_hash": password}  # In real app, hash password
        )
        
        if response:
            _, payload = response
            if payload["status"] == "success":
                self.current_user = username
                print("Logged in successfully!")
            else:
                print("Login failed!")
                
    def list_accounts(self):
        """List accounts matching a pattern"""
        pattern = input("Search pattern (or press Enter for all): ").strip() or "*"
        page_size = 10
        page = 1
        
        while True:
            response = self.send_command(
                json_protocol.Command.LIST_ACCOUNTS,
                {"pattern": pattern, "page": page, "page_size": page_size}
            )
            
            if not response:
                break
                
            _, payload = response
            if payload["status"] != "success":
                print(f"Error: {payload['message']}")
                break
                
            accounts = payload["accounts"]
            total_pages = payload["total_pages"]
            
            print("\nAccounts:")
            for account in accounts:
                print(f"  - {account}")
            print(f"\nPage {page}/{total_pages}")
            
            if page < total_pages:
                if input("Press Enter for next page or 'q' to quit: ").lower() == 'q':
                    break
                page += 1
            else:
                break

    def main_loop(self):
        """Main client loop"""
        commands = {
            "1": ("Create account", self.create_account),
            "2": ("Login", self.login),
            "3": ("List accounts", self.list_accounts),
            "4": ("Quit", lambda: "quit")
        }
        
        while True:
            print("\nAvailable commands:")
            for key, (name, _) in commands.items():
                print(f"{key}: {name}")
                
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
    parser = argparse.ArgumentParser(description="Chat client")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=9999, help="Server port")
    args = parser.parse_args()
    
    client = ChatClient(args.host, args.port)
    if client.connect():
        try:
            client.main_loop()
        finally:
            client.disconnect()

if __name__ == "__main__":
    main()
