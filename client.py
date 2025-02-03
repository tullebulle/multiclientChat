"""
Chat Application Client

This module implements the client-side functionality for a chat application.
It handles network communication with the server using both custom and JSON protocols.

The client supports:
- Connection management with the chat server
- Account creation and authentication
- Message sending and receiving
- Account management operations
"""

import socket
import json
from typing import Optional

class ChatClient:
    """
    Main client class handling all chat operations and server communication.
    
    Attributes:
        host (str): Server hostname or IP address
        port (int): Server port number
        socket (Optional[socket.socket]): Socket connection to server
    """

    def __init__(self, host: str = 'localhost', port: int = 9999):
        """
        Initialize a new chat client.

        Args:
            host (str): Server hostname or IP address. Defaults to 'localhost'.
            port (int): Server port number. Defaults to 9999.
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
    
    def connect(self) -> bool:
        """
        Establish connection to the chat server.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def disconnect(self) -> None:
        """
        Close the connection to the server if one exists.
        """
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def send_message(self, message: str) -> bool:
        """
        Send a message to the server.

        Args:
            message (str): The message to send.

        Returns:
            bool: True if message sent successfully, False otherwise.
        """
        if not self.socket:
            return False
        try:
            self.socket.send(message.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Send failed: {e}")
            return False
    
    def receive_message(self) -> Optional[str]:
        """
        Receive a message from the server.

        Returns:
            Optional[str]: The received message, or None if receive failed.
        """
        if not self.socket:
            return None
        try:
            return self.socket.recv(1024).decode('utf-8')
        except Exception as e:
            print(f"Receive failed: {e}")
            return None


def main():
    """
    Main entry point for the chat client application.
    Sets up a client instance and tests basic connectivity.
    """
    client = ChatClient()
    if client.connect():
        client.send_message("Hello, server!")
        response = client.receive_message()
        print(f"Server response: {response}")
        client.disconnect()


if __name__ == "__main__":
    main()
