"""
Command-line test client for the custom protocol chat server.
"""

import socket
import struct
import logging
from src.custom_protocol import custom_protocol
import sys

logging.basicConfig(level=logging.DEBUG)

class ChatClient:
    def __init__(self, host='localhost', port=9000):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.current_user = None
    
    def send_command(self, command, payload):
        """Send a command and get response"""
        message = custom_protocol.encode_message(command, payload)
        self.sock.sendall(message)
        
        # Read response header
        header = self.sock.recv(3)
        if not header or len(header) != 3:
            raise RuntimeError("Failed to receive response header")
            
        cmd_val, length = struct.unpack('!BH', header)
        cmd = custom_protocol.Command(cmd_val)
        
        # Read payload
        response = b''
        while len(response) < length:
            chunk = self.sock.recv(length - len(response))
            if not chunk:
                raise RuntimeError("Connection closed while reading response")
            response += chunk
            
        return cmd, response
    
    def login(self, username, password):
        """Login to the server"""
        payload = bytes([len(username)]) + username.encode()
        payload += bytes([len(password)]) + password.encode()
        cmd, response = self.send_command(custom_protocol.Command.AUTH, payload)
        success = response == b'\x01'
        if success:
            self.current_user = username
        return success
    
    def create_account(self, username, password):
        """Create a new account"""
        payload = bytes([len(username)]) + username.encode()
        payload += bytes([len(password)]) + password.encode()
        cmd, response = self.send_command(custom_protocol.Command.CREATE_ACCOUNT, payload)
        return response == b'\x01'
    
    def list_accounts(self, pattern="*"):
        """List accounts matching pattern"""
        payload = bytes([len(pattern)]) + pattern.encode()
        cmd, response = self.send_command(custom_protocol.Command.LIST_ACCOUNTS, payload)
        count = response[0]
        pos = 1
        accounts = []
        for _ in range(count):
            name_len = response[pos]
            name = response[pos+1:pos+1+name_len].decode()
            accounts.append(name)
            pos += 1 + name_len
        return accounts
    
    def send_message(self, recipient, content):
        """Send a message to another user"""
        if not self.current_user:
            raise RuntimeError("Not logged in")
            
        payload = bytes([len(recipient)]) + recipient.encode()
        payload += struct.pack('!H', len(content)) + content.encode()
        cmd, response = self.send_command(custom_protocol.Command.SEND_MESSAGE, payload)
        message_id = struct.unpack('!I', response[:4])[0]
        return message_id
    
    def get_messages(self, include_read=True):
        """Get messages"""
        if not self.current_user:
            raise RuntimeError("Not logged in")
            
        payload = bytes([int(include_read)])
        cmd, response = self.send_command(custom_protocol.Command.GET_MESSAGES, payload)
        
        count = struct.unpack('!H', response[:2])[0]
        pos = 2
        messages = []
        
        for _ in range(count):
            msg_id = struct.unpack('!I', response[pos:pos+4])[0]
            pos += 4
            
            sender_len = response[pos]
            pos += 1
            sender = response[pos:pos+sender_len].decode()
            pos += sender_len
            
            content_len = struct.unpack('!H', response[pos:pos+2])[0]
            pos += 2
            content = response[pos:pos+content_len].decode()
            pos += content_len
            
            timestamp = struct.unpack('!Q', response[pos:pos+8])[0]
            pos += 8
            
            is_read = bool(response[pos])
            pos += 1
            
            messages.append({
                'id': msg_id,
                'sender': sender,
                'content': content,
                'timestamp': timestamp,
                'is_read': is_read
            })
        
        return messages
    
    def mark_read(self, message_ids):
        """Mark messages as read"""
        if not self.current_user:
            raise RuntimeError("Not logged in")
            
        payload = struct.pack('!H', len(message_ids))
        for msg_id in message_ids:
            payload += struct.pack('!I', msg_id)
        
        cmd, response = self.send_command(custom_protocol.Command.MARK_READ, payload)
        return struct.unpack('!H', response)[0]
    
    def delete_messages(self, message_ids):
        """Delete messages"""
        if not self.current_user:
            raise RuntimeError("Not logged in")
            
        payload = struct.pack('!H', len(message_ids))
        for msg_id in message_ids:
            payload += struct.pack('!I', msg_id)
        
        cmd, response = self.send_command(custom_protocol.Command.DELETE_MESSAGES, payload)
        return struct.unpack('!H', response)[0]
    
    def close(self):
        """Close the connection"""
        self.sock.close()

def main():
    client = ChatClient()
    
    while True:
        if client.current_user:
            print(f"\nLogged in as: {client.current_user}")
        else:
            print("\nNot logged in")
            
        print("\nAvailable commands:")
        print("1. Create account")
        print("2. Login")
        print("3. List accounts")
        print("4. Send message")
        print("5. Get messages")
        print("6. Mark messages read")
        print("7. Delete messages")
        print("8. Exit")
        
        choice = input("\nEnter command number: ")
        
        try:
            if choice == '1':
                username = input("Username: ")
                password = input("Password: ")
                if client.create_account(username, password):
                    print("Account created successfully")
                else:
                    print("Failed to create account")
                    
            elif choice == '2':
                username = input("Username: ")
                password = input("Password: ")
                if client.login(username, password):
                    print("Login successful")
                else:
                    print("Login failed")
                    
            elif choice == '3':
                pattern = input("Search pattern (default *): ") or "*"
                accounts = client.list_accounts(pattern)
                print("\nAccounts:")
                for account in accounts:
                    print(f"- {account}")
                    
            elif choice == '4':
                if not client.current_user:
                    print("Please login first")
                    continue
                recipient = input("Recipient: ")
                content = input("Message: ")
                msg_id = client.send_message(recipient, content)
                print(f"Message sent (ID: {msg_id})")
                
            elif choice == '5':
                if not client.current_user:
                    print("Please login first")
                    continue
                include_read = input("Include read messages? (y/n): ").lower() == 'y'
                messages = client.get_messages(include_read)
                print("\nMessages:")
                for msg in messages:
                    status = "Read" if msg['is_read'] else "Unread"
                    print(f"[{msg['id']}] From {msg['sender']}: {msg['content']} ({status})")
                    
            elif choice == '6':
                if not client.current_user:
                    print("Please login first")
                    continue
                ids = input("Message IDs (comma-separated): ")
                message_ids = [int(id.strip()) for id in ids.split(',')]
                marked = client.mark_read(message_ids)
                print(f"Marked {marked} messages as read")
                
            elif choice == '7':
                if not client.current_user:
                    print("Please login first")
                    continue
                ids = input("Message IDs (comma-separated): ")
                message_ids = [int(id.strip()) for id in ids.split(',')]
                deleted = client.delete_messages(message_ids)
                print(f"Deleted {deleted} messages")
                
            elif choice == '8':
                break
                
            else:
                print("Invalid choice")
                
        except Exception as e:
            print(f"Error: {e}")
    
    client.close()

if __name__ == '__main__':
    main() 