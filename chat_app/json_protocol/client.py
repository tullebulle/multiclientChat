"""
JSON Protocol Chat Client

A command-line client using the JSON protocol.
"""

import socket
import argparse
import getpass
import sys
import logging
from chat_app.json_protocol import protocol

class JSONChatClient:
    """Interactive chat client using JSON protocol"""
    
    def __init__(self, host: str = 'localhost', port: int = 9998):  # Default to JSON port
        """Initialize the chat client"""
        self.host = host
        self.port = port
        self.socket = None
        self.current_user = None
        
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
            
    def send_command(self, command: protocol.Command, payload: dict) -> tuple:
        """Send a command to the server and get the response"""
        if not self.socket:
            print("Not connected to server")
            return None
            
        try:
            # Send command
            message = protocol.encode_message(command, payload)
            self.socket.sendall(message)
            
            # Get response
            response = self.socket.recv(4096)  # Larger buffer for JSON
            return protocol.decode_message(response)
        except Exception as e:
            print(f"Error sending command: {e}")
            return None
            
    def create_account(self):
        """Create a new account"""
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        
        payload = {
            "username": username,
            "password": password
        }
        
        response = self.send_command(protocol.Command.CREATE_ACCOUNT, payload)
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
        
        payload = {
            "username": username,
            "password_hash": password  # In real app, hash password
        }
        
        response = self.send_command(protocol.Command.AUTH, payload)
        if response:
            _, payload = response
            if payload["status"] == "success":
                self.current_user = username
                print("Logged in successfully!")
            else:
                print(f"Login failed: {payload['message']}")
                
    def list_accounts(self):
        """List accounts matching a pattern with pagination"""
        pattern = input("Search pattern (or press Enter for all): ").strip() or "*"
        page_size = 10
        page = 1
        
        while True:
            payload = {
                "pattern": pattern,
                "page": page,
                "page_size": page_size
            }
            
            response = self.send_command(protocol.Command.LIST_ACCOUNTS, payload)
            if not response:
                break
                
            _, payload = response
            if payload["status"] != "success":
                print(f"Error: {payload['message']}")
                break
                
            accounts = payload["accounts"]
            total_pages = payload["total_pages"]
            total_accounts = payload["total_accounts"]
            
            print("\nAccounts:")
            for account in accounts:
                print(f"  - {account}")
            print(f"\nPage {page}/{total_pages} (Total accounts: {total_accounts})")
            
            if page < total_pages:
                choice = input("\nPress Enter for next page, 'q' to quit: ").lower()
                if choice == 'q':
                    break
                page += 1
            else:
                if total_pages > 0:
                    input("\nPress Enter to continue...")
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
            if self.current_user:
                print(f"\nLogged in as: {self.current_user}")
                
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