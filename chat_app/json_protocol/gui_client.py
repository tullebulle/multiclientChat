"""
JSON Protocol GUI Client

A graphical client using the JSON protocol.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import socket
from datetime import datetime
from . import protocol

# Set up logging at the start of the file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class JSONChatClient:
    """JSON protocol chat client implementation"""
    def __init__(self, host='localhost', port=9998):
        self.host = host
        self.port = port
        self.socket = None
        self.current_user = None
        logging.debug(f"Initialized JSON client for {host}:{port}")
        
    def connect(self) -> bool:
        """Connect to the chat server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            logging.debug(f"Attempting to connect to {self.host}:{self.port}")
            self.socket.connect((self.host, self.port))
            logging.debug("Successfully connected to server")
            return True
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            return False
            
    def send_command(self, command: protocol.Command, payload: dict) -> tuple:
        """Send a command to the server and get the response"""
        if not self.socket:
            logging.error("Not connected to server")
            return None
            
        try:
            message = protocol.encode_message(command, payload)
            logging.debug(f"Sending command {command.name} with payload: {payload}")
            self.socket.sendall(message)
            response = self.socket.recv(4096)
            decoded_response = protocol.decode_message(response)
            logging.debug(f"Received response: {decoded_response}")
            return decoded_response
        except Exception as e:
            logging.error(f"Error sending command: {e}")
            return None

class JSONChatGUIClient:
    def __init__(self, host='localhost', port=9998):
        self.client = JSONChatClient(host, port)
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("JSON Chat Client")
        self.root.geometry("800x600")
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Initialize message_list before creating tabs
        self.message_list = None
        self.message_ids = {}
        
        # Create tabs
        self.create_login_tab()
        self.create_chat_tab()
        
        # Disable chat tab initially
        self.notebook.tab(1, state='disabled')
        
    def create_login_tab(self):
        """Create the login/registration tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text='Login')
        
        # Login section
        login_frame = ttk.LabelFrame(frame, text="Login", padding=10)
        login_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(login_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5)
        self.login_username = ttk.Entry(login_frame)
        self.login_username.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(login_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5)
        self.login_password = ttk.Entry(login_frame, show="*")
        self.login_password.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Button(login_frame, text="Login", 
                   command=self.handle_login).grid(row=2, column=0, columnspan=2, pady=10)
        
        # Registration section
        reg_frame = ttk.LabelFrame(frame, text="Create Account", padding=10)
        reg_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(reg_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5)
        self.reg_username = ttk.Entry(reg_frame)
        self.reg_username.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(reg_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5)
        self.reg_password = ttk.Entry(reg_frame, show="*")
        self.reg_password.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Button(reg_frame, text="Create Account", 
                   command=self.handle_register).grid(row=2, column=0, columnspan=2, pady=10)
        
        # Delete Account section
        delete_frame = ttk.LabelFrame(frame, text="Delete Account", padding=10)
        delete_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(delete_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5)
        self.delete_username = ttk.Entry(delete_frame)
        self.delete_username.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(delete_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5)
        self.delete_password = ttk.Entry(delete_frame, show="*")
        self.delete_password.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Button(delete_frame, text="Delete Account", 
                   command=self.handle_delete_account,
                   style='Danger.TButton').grid(row=2, column=0, columnspan=2, pady=10)
        
        return frame

    def create_chat_tab(self):
        """Create the main chat tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text='Chat')
        
        # Split into left and right panes
        left_pane = ttk.Frame(frame)
        left_pane.pack(side='left', fill='y', padx=5, pady=5)
        
        right_pane = ttk.Frame(frame)
        right_pane.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
        # === Left Pane Contents ===
        # Search section
        ttk.Label(left_pane, text="Search Users:").pack(anchor='w')
        search_frame = ttk.Frame(left_pane)
        search_frame.pack(fill='x', pady=2)
        
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side='left', expand=True, fill='x')
        
        ttk.Button(search_frame, text="Search", 
                   command=self.perform_search).pack(side='right', padx=2)
        
        # User list
        self.user_listbox = tk.Listbox(left_pane, width=20, height=15)
        self.user_listbox.pack(fill='both', expand=True, pady=5)
        
        # === Right Pane Contents ===
        # Top info bar
        info_frame = ttk.Frame(right_pane)
        info_frame.pack(fill='x', pady=5)
        
        self.login_label = ttk.Label(info_frame, text="Not logged in")
        self.login_label.pack(side='left')
        
        ttk.Button(info_frame, text="↻ Refresh", 
                   command=self.refresh_messages).pack(side='right')
        
        # Messages area
        messages_frame = ttk.Frame(right_pane)
        messages_frame.pack(fill='both', expand=True)
        
        self.message_list = ttk.Treeview(
            messages_frame,
            columns=('Time', 'From', 'Message'),
            show='headings',
            selectmode='extended'
        )
        
        self.message_list.heading('Time', text='Time')
        self.message_list.heading('From', text='From')
        self.message_list.heading('Message', text='Message')
        
        self.message_list.column('Time', width=70)
        self.message_list.column('From', width=100)
        self.message_list.column('Message', width=300)
        
        scrollbar = ttk.Scrollbar(messages_frame, orient='vertical', 
                                 command=self.message_list.yview)
        self.message_list.configure(yscrollcommand=scrollbar.set)
        
        self.message_list.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Message controls
        controls_frame = ttk.Frame(right_pane)
        controls_frame.pack(fill='x', pady=5)
        
        ttk.Button(controls_frame, text="Mark Read", 
                   command=self.mark_selected_read).pack(side='left', padx=2)
        ttk.Button(controls_frame, text="Delete", 
                   command=self.delete_selected_messages).pack(side='left', padx=2)
        
        # Message input area - explicitly at the bottom
        input_frame = ttk.Frame(right_pane)
        input_frame.pack(side='bottom', fill='x', pady=5)
        
        self.message_input = ttk.Entry(input_frame)
        self.message_input.pack(side='left', fill='x', expand=True)
        
        ttk.Button(input_frame, text="Send", 
                   command=self.send_message).pack(side='right', padx=5)
        
        # Configure tags for message list
        self.message_list.tag_configure('unread', font=('TkDefaultFont', 9, 'bold'))
        self.message_list.tag_configure('read', font=('TkDefaultFont', 9))
        
        # Initialize message IDs dictionary
        self.message_ids = {}
        
        return frame

    def run(self):
        """Start the GUI application"""
        if self.client.connect():
            self.root.mainloop()
        else:
            messagebox.showerror("Error", "Could not connect to server") 

    def handle_login(self):
        """Handle login button click"""
        username = self.login_username.get().strip()
        password = self.login_password.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        payload = {
            "username": username,
            "password": password
        }
        
        response = self.client.send_command(protocol.Command.AUTH, payload)
        if response and response[1].get('status') == 'success':
            messagebox.showinfo("Success", "Logged in successfully!")
            self.client.current_user = username
            self.notebook.tab(1, state='normal')
            self.notebook.select(1)
            self.login_label.config(text=f"Logged in as: {username}")
            self.refresh_messages()
        else:
            messagebox.showerror("Error", "Login failed")

    def handle_register(self):
        """Handle register button click"""
        username = self.reg_username.get().strip()
        password = self.reg_password.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        payload = {
            "username": username,
            "password": password
        }
        
        response = self.client.send_command(protocol.Command.CREATE_ACCOUNT, payload)
        if response and response[1].get('status') == 'success':
            messagebox.showinfo("Success", "Account created successfully!")
            self.reg_username.delete(0, tk.END)
            self.reg_password.delete(0, tk.END)
        else:
            messagebox.showerror("Error", "Failed to create account")

    def handle_delete_account(self):
        """Handle delete account button click"""
        username = self.delete_username.get().strip()
        password = self.delete_password.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        # Check for unread messages if deleting current user's account
        if self.client.current_user == username:
            payload = {"include_read": False}
            response = self.client.send_command(protocol.Command.GET_MESSAGES, payload)
            
            if response and response[1].get('status') == 'success':
                unread_messages = response[1].get('messages', [])
                if unread_messages:
                    if not messagebox.askyesno("Warning", 
                                             f"You have {len(unread_messages)} unread messages!\n"
                                             "Are you sure you want to delete your account?\n"
                                             "This action cannot be undone!"):
                        return
        else:
            # Regular confirmation for non-logged-in deletion
            if not messagebox.askyesno("Confirm Delete", 
                                      "Are you sure you want to delete your account?\n"
                                      "This action cannot be undone!"):
                return
        
        # Try to delete account
        payload = {
            "username": username,
            "password": password
        }
        response = self.client.send_command(protocol.Command.DELETE_ACCOUNT, payload)
        
        if response and response[1].get('status') == 'success':
            messagebox.showinfo("Success", "Account deleted successfully")
            # Clear the fields
            self.delete_username.delete(0, tk.END)
            self.delete_password.delete(0, tk.END)
            # If currently logged in as this user, log out
            if self.client.current_user == username:
                self.notebook.tab(1, state='disabled')
                self.notebook.select(0)
                self.client.current_user = None
        else:
            error_msg = response[1].get('message') if response else "Unknown error"
            messagebox.showerror("Error", f"Failed to delete account: {error_msg}")

    def perform_search(self):
        """Handle user search"""
        raw_pattern = self.search_entry.get().strip()
        # Add wildcards if not present and not empty
        pattern = f"*{raw_pattern}*" if raw_pattern and '*' not in raw_pattern else (raw_pattern or "*")
        logging.info(f"Performing search with pattern: {pattern}")
        
        payload = {
            "pattern": pattern
        }
        
        logging.debug(f"Sending search request with payload: {payload}")
        response = self.client.send_command(protocol.Command.LIST_ACCOUNTS, payload)
        logging.debug(f"Received search response: {response}")
        
        if response and response[1].get('status') == 'success':
            self.user_listbox.delete(0, tk.END)  # Clear current list
            accounts = response[1].get('accounts', [])
            logging.info(f"Found {len(accounts)} accounts: {accounts}")
            for user in accounts:
                if user != self.client.current_user:  # Don't show current user
                    logging.debug(f"Adding user to list: {user}")
                    self.user_listbox.insert(tk.END, user)
        else:
            error_msg = response[1].get('message') if response else "Unknown error"
            logging.error(f"Search failed: {error_msg}")
            messagebox.showerror("Error", f"Failed to search users: {error_msg}")

    def send_message(self):
        """Send a message to selected user"""
        if not self.user_listbox.curselection():
            messagebox.showwarning("Warning", "Please select a recipient")
            return
        
        recipient = self.user_listbox.get(self.user_listbox.curselection())
        content = self.message_input.get().strip()
        
        if not content:
            return
        
        logging.debug(f"Sending message to {recipient}: {content}")
        
        payload = {
            "recipient": recipient,
            "content": content
        }
        
        response = self.client.send_command(protocol.Command.SEND_MESSAGE, payload)
        if response and response[1].get('status') == 'success':
            logging.debug("Message sent successfully")
            self.message_input.delete(0, tk.END)
            self.refresh_messages()  # Refresh after sending
        else:
            error_msg = response[1].get('message') if response else "Unknown error"
            logging.error(f"Failed to send message: {error_msg}")
            messagebox.showerror("Error", f"Failed to send message: {error_msg}")

    def refresh_messages(self):
        """Manually refresh messages"""
        if not self.client.current_user:
            return
        
        try:
            payload = {
                "include_read": True
            }
            
            response = self.client.send_command(protocol.Command.GET_MESSAGES, payload)
            if response and response[1].get('status') == 'success':
                # Clear existing messages
                for item in self.message_list.get_children():
                    self.message_list.delete(item)
                self.message_ids.clear()
                
                # Add messages to treeview
                messages = response[1].get('messages', [])
                for msg in sorted(messages, key=lambda x: x['timestamp']):
                    timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M:%S')
                    item_id = self.message_list.insert('', 'end',
                        values=(timestamp, msg['sender'], msg['content']),
                        tags=('unread' if not msg['is_read'] else 'read',))
                    self.message_ids[item_id] = msg['id']
                
            else:
                error_msg = response[1].get('message') if response else "Unknown error"
                logging.error(f"Failed to refresh messages: {error_msg}")
                messagebox.showerror("Error", f"Failed to refresh messages: {error_msg}")
                
        except Exception as e:
            logging.error(f"Error refreshing messages: {e}")
            messagebox.showerror("Error", "Failed to refresh messages")

    def mark_selected_read(self):
        """Mark selected messages as read"""
        selected_items = self.message_list.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select messages to mark as read")
            return
        
        message_ids = [self.message_ids[item] for item in selected_items]
        payload = {
            "message_ids": message_ids
        }
        
        response = self.client.send_command(protocol.Command.MARK_READ, payload)
        if response and response[1].get('status') == 'success':
            self.refresh_messages()
        else:
            messagebox.showerror("Error", "Failed to mark messages as read")

    def delete_selected_messages(self):
        """Delete selected messages"""
        selected_items = self.message_list.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select messages to delete")
            return
        
        if messagebox.askyesno("Confirm Delete", 
                              f"Delete {len(selected_items)} selected messages?"):
            message_ids = [self.message_ids[item] for item in selected_items]
            payload = {
                "message_ids": message_ids
            }
            
            response = self.client.send_command(protocol.Command.DELETE_MESSAGES, payload)
            if response and response[1].get('status') == 'success':
                messagebox.showinfo("Success", "Messages deleted")
                self.refresh_messages()
            else:
                messagebox.showerror("Error", "Failed to delete messages") 