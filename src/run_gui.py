"""
Chat GUI Application

This module provides a graphical user interface for interacting with the chat
server. It supports both JSON and custom binary protocols.

Usage:
    python run_gui.py [--server SERVER] [--protocol {json,custom,grpc}]

Example:
    # Connect to a single server
    python run_gui.py --server localhost:9999 --protocol json
    
    # Connect to a cluster of servers for fault tolerance
    python run_gui.py --server localhost:9001,localhost:9002,localhost:9003 --protocol grpc
"""

import argparse
import logging
import signal
import sys
import os
import hashlib
import time
import tkinter as tk
from tkinter import ttk, messagebox
import threading

# Add parent directory to Python path to handle imports when run from different locations
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.json_protocol.client import JSONChatClient
from src.custom_protocol.client import CustomChatClient
from src.grpc_protocol.client import GRPCChatClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("grpc_client.log"),
        logging.StreamHandler()
    ]
)

# Set higher log level for grpc to avoid noise
logging.getLogger('grpc').setLevel(logging.WARNING)

class ChatGUI:
    """
    GUI for the chat application.
    
    Provides a graphical interface for logging in, creating accounts,
    sending and receiving messages.
    """
    
    def __init__(self, client):
        """
        Initialize the chat GUI.
        
        Args:
            client: Chat client instance (JSON, custom, or gRPC)
        """
        self.client = client
        self.root = tk.Tk()
        self.root.title("Chat Application")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Set up the frames
        self.login_frame = ttk.Frame(self.root, padding=10)
        self.chat_frame = ttk.Frame(self.root, padding=10)
        
        # Create widgets
        self.create_login_frame()
        self.create_chat_frame()
        
        # Show login frame initially
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        
        # Set up refresh timer
        self.refresh_timer = None
        
        # Set up message refresh
        self.message_list = []
        self.user_list = []
        
        # Check cluster status if using gRPC client
        if isinstance(self.client, GRPCChatClient):
            self.check_cluster_status()
    
    def create_login_frame(self):
        """Create the login/registration frame"""
        frame = self.login_frame
        
        # Username
        ttk.Label(frame, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.username_var).grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        # Password
        ttk.Label(frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.password_var, show="*").grid(row=1, column=1, sticky=tk.EW, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Login", command=self.login).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Create Account", command=self.create_account).pack(side=tk.LEFT, padx=5)
        
        # Status
        self.login_status_var = tk.StringVar()
        ttk.Label(frame, textvariable=self.login_status_var, foreground="red").grid(row=3, column=0, columnspan=2, pady=5)
        
        # Server status (for gRPC fault-tolerant clients)
        if isinstance(self.client, GRPCChatClient):
            ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=10)
            ttk.Label(frame, text="Server Status:").grid(row=5, column=0, sticky=tk.W)
            
            self.server_status_var = tk.StringVar(value="Checking server status...")
            ttk.Label(frame, textvariable=self.server_status_var).grid(row=5, column=1, sticky=tk.W)
            
            ttk.Button(frame, text="Refresh Status", command=self.check_cluster_status).grid(row=6, column=0, columnspan=2, pady=5)
        
        # Configure grid
        frame.columnconfigure(1, weight=1)
    
    def create_chat_frame(self):
        """Create the main chat interface frame"""
        frame = self.chat_frame
        
        # Split into left and right panes
        left_pane = ttk.Frame(frame)
        left_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_pane = ttk.Frame(frame, width=200)
        right_pane.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Left pane: Messages
        message_frame = ttk.LabelFrame(left_pane, text="Messages")
        message_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Message display
        self.message_display = tk.Text(message_frame, state=tk.DISABLED, wrap=tk.WORD)
        message_scroll = ttk.Scrollbar(message_frame, command=self.message_display.yview)
        self.message_display.config(yscrollcommand=message_scroll.set)
        
        self.message_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        message_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Compose message
        compose_frame = ttk.Frame(left_pane)
        compose_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(compose_frame, text="To:").pack(side=tk.LEFT)
        self.recipient_var = tk.StringVar()
        self.recipient_combo = ttk.Combobox(compose_frame, textvariable=self.recipient_var)
        self.recipient_combo.pack(side=tk.LEFT, padx=5)
        
        # Message entry
        message_entry_frame = ttk.Frame(left_pane)
        message_entry_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.message_var = tk.StringVar()
        ttk.Entry(message_entry_frame, textvariable=self.message_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(message_entry_frame, text="Send", command=self.send_message).pack(side=tk.RIGHT)
        
        # Right pane: User list and controls
        user_frame = ttk.LabelFrame(right_pane, text="Users")
        user_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.user_listbox = tk.Listbox(user_frame)
        user_scroll = ttk.Scrollbar(user_frame, command=self.user_listbox.yview)
        self.user_listbox.config(yscrollcommand=user_scroll.set)
        
        self.user_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        user_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.user_listbox.bind('<<ListboxSelect>>', self.on_user_select)
        
        # Control buttons
        button_frame = ttk.Frame(right_pane)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Refresh", command=self.refresh_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Logout", command=self.logout).pack(side=tk.RIGHT, padx=2)
        
        # Server status (for gRPC fault-tolerant clients)
        if isinstance(self.client, GRPCChatClient):
            status_frame = ttk.LabelFrame(right_pane, text="Cluster Status")
            status_frame.pack(fill=tk.X, padx=5, pady=5)
            
            self.cluster_status_text = tk.Text(status_frame, height=5, state=tk.DISABLED)
            self.cluster_status_text.pack(fill=tk.X, padx=5, pady=5)
            
            ttk.Button(status_frame, text="Refresh Status", command=self.check_cluster_status).pack(pady=5)
    
    def hash_password(self, password):
        """Create SHA-256 hash of the password"""
        hasher = hashlib.sha256()
        hasher.update(password.encode('utf-8'))
        return hasher.hexdigest()
    
    def login(self):
        """Handle user login"""
        username = self.username_var.get()
        password = self.password_var.get()
        
        if not username or not password:
            self.login_status_var.set("Username and password required")
            return
        
        logging.info(f"Attempting to log in with username: {username}")
        
        # Hash password
        password_hash = self.hash_password(password)
        logging.debug(f"Generated password hash: {password_hash[:10]}...")
        
        # Attempt login
        success, error = self.client.login(username, password_hash)
        
        if success:
            logging.info(f"Login successful for user: {username}")
            self.login_frame.pack_forget()
            self.chat_frame.pack(fill=tk.BOTH, expand=True)
            self.root.title(f"Chat - {username}")
            self.refresh_data()
            self.start_refresh_timer()
        else:
            logging.warning(f"Login failed for user '{username}': {error}")
            # Check if this is a connection error
            if "connection" in error.lower() or "unavailable" in error.lower():
                self.login_status_var.set(f"Server connection error: {error}")
            else:
                self.login_status_var.set(f"Login failed: {error}")
                
            # Try to check if the user exists
            try:
                users, _ = self.client.list_accounts()
                if username not in users:
                    self.login_status_var.set(f"User '{username}' does not exist")
                    logging.warning(f"Attempted login with non-existent user: {username}")
            except:
                pass
    
    def create_account(self):
        """Handle account creation"""
        username = self.username_var.get()
        password = self.password_var.get()
        
        if not username or not password:
            self.login_status_var.set("Username and password required")
            return
        
        # Hash password
        password_hash = self.hash_password(password)
        
        # Create account
        success, error = self.client.create_account(username, password_hash)
        
        if success:
            self.login_status_var.set("Account created! You can now login.")
        else:
            # Format the error message
            if "already exists" in error.lower():
                self.login_status_var.set(f"Account already exists: {username}")
            else:
                self.login_status_var.set(f"Account creation failed: {error}")
            logging.warning(f"Failed to create account: {error}")
    
    def logout(self):
        """Handle user logout"""
        self.stop_refresh_timer()
        self.client.close()
        self.chat_frame.pack_forget()
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        self.root.title("Chat Application")
        self.username_var.set("")
        self.password_var.set("")
        self.login_status_var.set("")
    
    def send_message(self):
        """Send a message"""
        recipient = self.recipient_var.get()
        content = self.message_var.get()
        
        if not recipient or not content:
            messagebox.showerror("Error", "Please specify a recipient and message")
            return
        
        # Send the message
        msg_id, error = self.client.send_message(recipient, content)
        
        if msg_id > 0:
            self.message_var.set("")  # Clear message field
            self.refresh_messages()  # Refresh to show the sent message
        else:
            messagebox.showerror("Error", f"Failed to send message: {error}")
    
    def on_user_select(self, event):
        """Handle user selection from listbox"""
        selection = self.user_listbox.curselection()
        if selection:
            user = self.user_listbox.get(selection[0])
            self.recipient_var.set(user)
    
    def refresh_data(self):
        """Refresh user list and messages"""
        self.refresh_users()
        self.refresh_messages()
    
    def refresh_users(self):
        """Update the user list"""
        try:
            users, error = self.client.list_accounts()
            
            if error:
                logging.error(f"Error listing users: {error}")
                return
                
            # Update the listbox
            self.user_listbox.delete(0, tk.END)
            self.user_list = sorted(users)
            
            for user in self.user_list:
                self.user_listbox.insert(tk.END, user)
            
            # Update the recipient dropdown
            self.recipient_combo['values'] = self.user_list
        except Exception as e:
            logging.error(f"Error refreshing users: {e}")
    
    def refresh_messages(self):
        """Update the message display"""
        try:
            messages, error = self.client.get_messages(include_read=True)
            
            if error:
                logging.error(f"Error getting messages: {error}")
                return
            
            # Clear current display
            self.message_display.config(state=tk.NORMAL)
            self.message_display.delete(1.0, tk.END)
            
            # Display messages
            for msg in messages:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(msg['timestamp']))
                
                if msg['sender'] == self.client.username:
                    # Outgoing message
                    header = f"To {msg['recipient']} at {timestamp}:\n"
                    self.message_display.insert(tk.END, header, "outgoing_header")
                else:
                    # Incoming message
                    header = f"From {msg['sender']} at {timestamp}:\n"
                    self.message_display.insert(tk.END, header, "incoming_header")
                
                self.message_display.insert(tk.END, f"{msg['content']}\n\n")
            
            self.message_display.config(state=tk.DISABLED)
            
            # Mark messages as read
            unread_ids = [msg['id'] for msg in messages if not msg['is_read']]
            if unread_ids:
                self.client.mark_read(unread_ids)
        except Exception as e:
            logging.error(f"Error refreshing messages: {e}")
    
    def check_cluster_status(self):
        """Check and display the status of the server cluster (gRPC only)"""
        if not isinstance(self.client, GRPCChatClient):
            return
        
        try:
            # Check if client stub is None (disconnected)
            if self.client.stub is None:
                # Try to reconnect
                if not self.client.connect():
                    # Still disconnected - show error
                    error_message = "Disconnected: No server available"
                    if hasattr(self, 'server_status_var'):
                        self.server_status_var.set(error_message)
                    
                    if hasattr(self, 'cluster_status_text'):
                        self.cluster_status_text.config(state=tk.NORMAL)
                        self.cluster_status_text.delete(1.0, tk.END)
                        self.cluster_status_text.insert(tk.END, 
                            "Connection Error: All servers unavailable\n\n"
                            "Please check if servers are running.\n"
                            "You may need to restart with all servers specified:\n"
                            "python src/run_gui.py --server localhost:9001,localhost:9002,localhost:9003"
                        )
                        self.cluster_status_text.config(state=tk.DISABLED)
                    return
            
            # Get status as normal
            status, error = self.client.get_cluster_status()
            
            if error:
                # Show error but try to reconnect
                status_text = f"Error getting status: {error}"
                if hasattr(self, 'server_status_var'):
                    self.server_status_var.set(status_text)
                
                if hasattr(self, 'cluster_status_text'):
                    self.cluster_status_text.config(state=tk.NORMAL)
                    self.cluster_status_text.delete(1.0, tk.END)
                    self.cluster_status_text.insert(tk.END, 
                        f"Error: {error}\n\n"
                        f"Attempting to connect to alternate servers...\n\n"
                        f"If this persists, restart with all servers:\n"
                        f"python src/run_gui.py --server localhost:9001,localhost:9002,localhost:9003"
                    )
                    self.cluster_status_text.config(state=tk.DISABLED)
                    
                    # Try to reconnect to any available server
                    if self.client.connect():
                        self.after(1000, self.check_cluster_status)
                return
            
            # All is well - display the status
            status_text = (
                f"Node: {status['node_id']} ({status['state']})\n"
                f"Leader: {status['leader_id'] or 'Unknown'}\n"
                f"Term: {status['current_term']}\n"
                f"Peers: {status['peer_count']}\n"
                f"Log entries: {status['log_count']}"
            )
            
            # Update status text in login frame
            if hasattr(self, 'server_status_var'):
                server_text = f"Connected to {status['node_id']} ({status['state']})"
                self.server_status_var.set(server_text)
            
            # Update status text in chat frame
            if hasattr(self, 'cluster_status_text'):
                self.cluster_status_text.config(state=tk.NORMAL)
                self.cluster_status_text.delete(1.0, tk.END)
                self.cluster_status_text.insert(tk.END, status_text)
                self.cluster_status_text.config(state=tk.DISABLED)
            
        except Exception as e:
            logging.error(f"Error checking cluster status: {e}")
            error_message = f"Error: {str(e)}"
            
            # Update status text
            if hasattr(self, 'server_status_var'):
                self.server_status_var.set(error_message)
            
            if hasattr(self, 'cluster_status_text'):
                self.cluster_status_text.config(state=tk.NORMAL)
                self.cluster_status_text.delete(1.0, tk.END)
                self.cluster_status_text.insert(tk.END, 
                    f"Error: Connection problem\n\n"
                    f"{str(e)}\n\n"
                    f"Attempting to reconnect..."
                )
                self.cluster_status_text.config(state=tk.DISABLED)
                
                # Try to reconnect
                if self.client.connect():
                    self.after(1000, self.check_cluster_status)
    
    def start_refresh_timer(self):
        """Start the timer for periodic data refresh"""
        self.refresh_data()  # Initial refresh
        self.refresh_timer = self.root.after(5000, self.start_refresh_timer)  # Refresh every 5 seconds
    
    def stop_refresh_timer(self):
        """Stop the refresh timer"""
        if self.refresh_timer:
            self.root.after_cancel(self.refresh_timer)
            self.refresh_timer = None
    
    def on_close(self):
        """Handle window close event"""
        self.stop_refresh_timer()
        self.client.close()
        self.root.destroy()
    
    def run(self):
        """Run the GUI main loop"""
        self.root.mainloop()

def main():
    """
    Main entry point for the chat GUI application.
    """
    parser = argparse.ArgumentParser(description="Chat client GUI")
    parser.add_argument(
        "--server",
        default="localhost:9001",
        help="Server address in format 'host:port' or comma-separated list of addresses for fault tolerance"
    )
    parser.add_argument(
        "--protocol",
        choices=["json", "custom", "grpc"],
        default="grpc",
        help="Protocol to use"
    )
    
    args = parser.parse_args()
    
    try:
        # Create appropriate client based on protocol
        if args.protocol == "json":
            host, port = args.server.split(":")
            client = JSONChatClient(host, int(port))
        elif args.protocol == "custom":
            host, port = args.server.split(":")
            client = CustomChatClient(host, int(port))
        elif args.protocol == "grpc":
            try:
                client = GRPCChatClient(args.server)
            except Exception as e:
                logging.error(f"Connection error: {e}")
                print(f"Warning: Connection to server failed: {e}")
                print("The GUI will start, but you may need to refresh the connection later.")
                
                # Create client but with stub set to None
                client = GRPCChatClient(args.server)
                client.stub = None  # Mark as disconnected
        
        # Create and run GUI
        gui = ChatGUI(client)
        gui.run()
        
    except ConnectionError as e:
        logging.error(f"Connection error: {e}")
        print(f"Failed to connect: {e}")
        
        # Instead of just exiting, create an offline GUI
        if args.protocol == "grpc":
            print("Starting GUI in offline mode. You can retry connecting later.")
            offline_client = GRPCChatClient(args.server, allow_connection_failure=True)
            gui = ChatGUI(offline_client)
            gui.run()
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 