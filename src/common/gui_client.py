"""
GUI Client for Custom Protocol Chat

A graphical interface using tkinter for the chat client. This module provides a complete
GUI implementation supporting both Custom Binary and JSON protocols.

Key Features:
- User authentication and account management
- Real-time messaging with auto-refresh
- Message status tracking (read/unread)
- User search with pagination
- Message deletion and read status management
- Dynamic message wrapping and display

The GUI is organized into two main tabs:
1. Login/Account Management
2. Chat Interface with user list and messages
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from src.custom_protocol import protocol
from ..custom_protocol.client import CustomChatClient
from ..json_protocol.client import JSONChatClient
import argparse

class ChatGUI:
    """
    Main GUI class for the chat application.
    
    This class implements a complete chat interface using tkinter, supporting both
    Custom Binary and JSON protocols. It provides a two-tab interface for login/account
    management and chat functionality.
    
    Attributes:
        client: The protocol client (either CustomChatClient or JSONChatClient)
        root: The main tkinter window
        notebook: Tab container for login and chat interfaces
        current_page: Current page number for user list pagination
        page_size: Number of users to display per page
        refresh_interval: Time between auto-refresh attempts (milliseconds)
        message_ids: Dictionary mapping treeview items to message IDs
        
    The GUI automatically refreshes messages for logged-in users and maintains
    message selection state during refreshes.
    """
    
    def __init__(self, host="localhost", port=9999, protocol="custom"):
        """
        Initialize the chat GUI.
        
        Args:
            host: Server hostname or IP (default: "localhost")
            port: Server port number (default: 9999)
            protocol: Protocol to use ("custom" or "json", default: "custom")
            
        The constructor sets up the main window, initializes the appropriate protocol
        client, and creates the tab-based interface.
        """
        if protocol == "custom":
            self.client = CustomChatClient(host=host, port=port)
        else:
            self.client = JSONChatClient(host=host, port=port)

        if not self.client.connect():
            messagebox.showerror("Error", "Could not connect to server!")
            return
        
        self.protocol = protocol

        # Main window setup
        self.root = tk.Tk()
        self.root.title("Chat Application")
        self.root.geometry("800x600")
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Create tabs
        self.login_frame = self.create_login_tab()
        self.chat_frame = self.create_chat_tab()
        
        # Initially disable chat tab
        self.notebook.tab(1, state='disabled')
        
        # Setup logging
        logging.basicConfig(level=logging.DEBUG)
        
        # Add refresh interval (in milliseconds)
        self.refresh_interval = 1000  # 5 seconds
        self.schedule_refresh()
        
    def create_login_tab(self):
        """
        Create the login/registration tab.
        
        This tab contains three sections:
        1. Login - For existing user authentication
        2. Create Account - For new user registration
        3. Delete Account - For account removal
        
        Each section contains username/password fields and appropriate action buttons.
        The tab is initially active while the chat tab is disabled until login.
        
        Returns:
            ttk.Frame: The constructed login tab frame
        """
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
        
        ttk.Button(login_frame, text="Login", command=self.handle_login).grid(row=2, column=0, columnspan=2, pady=10)
        
        # Registration section
        reg_frame = ttk.LabelFrame(frame, text="Create Account", padding=10)
        reg_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(reg_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5)
        self.reg_username = ttk.Entry(reg_frame)
        self.reg_username.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(reg_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5)
        self.reg_password = ttk.Entry(reg_frame, show="*")
        self.reg_password.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Button(reg_frame, text="Create Account", command=self.handle_register).grid(row=2, column=0, columnspan=2, pady=10)
        
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
        
        # Top frame for user info, refresh, and message limit
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill='x', padx=5, pady=5)
        
        # User info and refresh button side by side
        self.login_label = ttk.Label(top_frame, text="Not logged in", font=('TkDefaultFont', 10, 'bold'))
        self.login_label.pack(side='left', anchor='w')
        
        # Add message limit control
        limit_frame = ttk.Frame(top_frame)
        limit_frame.pack(side='right', padx=5)
        
        ttk.Label(limit_frame, text="Messages to show:").pack(side='left', padx=2)
        self.message_limit = ttk.Spinbox(limit_frame, from_=1, to=100, width=5)
        self.message_limit.set(10)  # Default value
        self.message_limit.pack(side='left', padx=2)
        
        ttk.Button(top_frame, text="↻ Refresh Messages", 
                   command=self.refresh_messages).pack(side='right', padx=5)
        
        # Left side - User list with search
        left_frame = ttk.Frame(frame)
        left_frame.pack(side='left', fill='y', padx=5, pady=5)
        
        # Search frame
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill='x', pady=5)
        
        ttk.Label(search_frame, text="Search Users:").pack(anchor='w')
        
        search_input_frame = ttk.Frame(search_frame)
        search_input_frame.pack(fill='x', pady=2)
        
        self.search_entry = ttk.Entry(search_input_frame, width=12)
        self.search_entry.pack(side='left')
        
        ttk.Button(search_input_frame, text="Search", 
                   command=self.perform_search,
                   width=6).pack(side='left', padx=2)
        
        # Add pagination controls
        pagination_frame = ttk.Frame(search_frame)
        pagination_frame.pack(fill='x', pady=2)
        
        self.prev_page_btn = ttk.Button(pagination_frame, text="←", 
                                       command=self.prev_page, width=3)
        self.prev_page_btn.pack(side='left', padx=2)
        
        self.page_label = ttk.Label(pagination_frame, text="Page 1")
        self.page_label.pack(side='left', padx=5)
        
        self.next_page_btn = ttk.Button(pagination_frame, text="→", 
                                       command=self.next_page, width=3)
        self.next_page_btn.pack(side='left', padx=2)
        
        self.current_page = 1
        self.page_size = 100  # Changed from 20 to 5 users per page
        
        self.user_listbox = tk.Listbox(left_frame, width=20)
        self.user_listbox.pack(fill='y', expand=True)
        
        # Right side - Messages
        right_frame = ttk.Frame(frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
        # Message list frame with checkboxes
        message_frame = ttk.Frame(right_frame)
        message_frame.pack(fill='both', expand=True)
        
        # Message list with checkboxes
        self.message_list = ttk.Treeview(message_frame, columns=('Time', 'From', 'Message'), 
                                        show='headings', selectmode='extended')
        self.message_list.heading('Time', text='Time')
        self.message_list.heading('From', text='From')
        self.message_list.heading('Message', text='Message')
        
        # Bind double-click event to show full message
        self.message_list.bind('<Double-1>', self.show_full_message)
        
        # Set column widths and stretch behavior
        self.message_list.column('Time', width=70, minwidth=70, stretch=False)
        self.message_list.column('From', width=100, minwidth=100, stretch=False)
        self.message_list.column('Message', width=300, minwidth=200, stretch=True)
        
        # Add binding for dynamic message wrapping
        def on_treeview_resize(event):
            message_col_width = self.message_list.winfo_width() - 170  # Subtract width of other columns
            self.message_list.column('Message', width=max(300, message_col_width))
        
        self.message_list.bind('<Configure>', on_treeview_resize)
        
        # Configure tag styles for read/unread
        self.message_list.tag_configure('unread', font=('TkDefaultFont', 10, 'bold'))
        self.message_list.tag_configure('read', font=('TkDefaultFont', 10))
        
        self.message_list.pack(side='left', fill='both', expand=True)
        
        # Scrollbar for message list
        scrollbar = ttk.Scrollbar(message_frame, orient='vertical', command=self.message_list.yview)
        scrollbar.pack(side='right', fill='y')
        self.message_list.configure(yscrollcommand=scrollbar.set)
        
        # Buttons frame
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill='x', pady=5)
        
        ttk.Button(button_frame, text="Delete Selected", 
                   command=self.delete_selected_messages).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Mark Selected as Read", 
                   command=self.mark_selected_read).pack(side='left', padx=5)
        
        # Message input area
        input_frame = ttk.Frame(right_frame)
        input_frame.pack(fill='x', pady=5)
        
        self.message_input = ttk.Entry(input_frame)
        self.message_input.pack(side='left', fill='x', expand=True)
        
        ttk.Button(input_frame, text="Send", command=self.send_message).pack(side='right', padx=5)
        
        # Store message IDs for deletion
        self.message_ids = {}  # Maps treeview item IDs to message IDs
        
        return frame
        
    def handle_login(self):
        """Handle login button click"""
        username = self.login_username.get().strip()
        password = self.login_password.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        success = self.client.login(username, password)
            
        if success:
            messagebox.showinfo("Success", "Logged in successfully!")
            self.notebook.tab(1, state='normal')
            self.notebook.select(1)
            self.login_label.config(text=f"Logged in as: {username}")
            self.search_entry.delete(0, tk.END)
            self.perform_search()
            self.refresh_messages()  # Initial message load
            # No need to explicitly start refresh - it's already scheduled
        else:
            messagebox.showerror("Error", "Login failed")
            
    def handle_register(self):
        """Handle registration button click"""
        username = self.reg_username.get().strip()
        password = self.reg_password.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        success = self.client.create_account(username, password)
            
        if success:
            messagebox.showinfo("Success", "Account created successfully!")
            # Clear registration fields
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
        
        # Try to login as the user to check messages
        temp_client = None
        if self.client.current_user != username:
            # Create temporary client with same protocol
            if self.protocol == "custom":
                temp_client = CustomChatClient(host=self.client.host, port=self.client.port)
            else:
                temp_client = JSONChatClient(host=self.client.host, port=self.client.port)
            
            if not temp_client.connect() or not temp_client.login(username, password):
                messagebox.showerror("Error", "Failed to verify account. Please check your credentials.")
                return
            messages = temp_client.get_messages(include_read=False)
        else:
            messages = self.client.get_messages(include_read=False)
        
        # Check for unread messages
        if messages:
            if not messagebox.askyesno("Warning", 
                                      f"This account has {len(messages)} unread messages!\n"
                                      "Are you sure you want to delete your account?\n"
                                      "This action cannot be undone!"):
                if temp_client:
                    temp_client.disconnect()
                return
        else:
            # Regular confirmation for deletion without unread messages
            if not messagebox.askyesno("Confirm Delete", 
                                      "Are you sure you want to delete your account?\n"
                                      "This action cannot be undone!"):
                if temp_client:
                    temp_client.disconnect()
                return
        
        # Try to delete account
        if self.client.delete_account(username, password):
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
            messagebox.showerror("Error", "Failed to delete account. Please check your credentials.")
        
        # Clean up temporary client if used
        if temp_client:
            temp_client.disconnect()
            
    def refresh_users(self):
        """Refresh the user list"""
        self.user_listbox.delete(0, tk.END)  # Always clear the list first
        
        accounts = self.client.list_accounts()
        if accounts is not None:  # Check for None instead of truthiness
            for account in sorted(accounts):
                self.user_listbox.insert(tk.END, account)
                
    def send_message(self):
        """Send a message to selected user"""
        if not self.user_listbox.curselection():
            messagebox.showwarning("Warning", "Please select a recipient")
            return
        
        recipient = self.user_listbox.get(self.user_listbox.curselection())
        content = self.message_input.get().strip()
        
        if not content:
            return
        
        if self.client.send_message(recipient, content):
            self.message_input.delete(0, tk.END)
            self.refresh_messages()  # Refresh after sending
        
    def refresh_messages(self):
        """Manually refresh messages while preserving selection"""
        if not self.client.current_user:
            return
        
        try:
            messages = self.client.get_messages(include_read=True)
            
            # Store currently selected items before refresh
            selected_items = self.message_list.selection()
            selected_contents = {
                self.message_list.item(item)['values'][2]: item  # Using message content as key
                for item in selected_items
            }
            
            # Clear existing messages
            for item in self.message_list.get_children():
                self.message_list.delete(item)
            self.message_ids.clear()
            
            # Sort messages by timestamp and limit the number shown
            limit = int(self.message_limit.get())
            sorted_messages = sorted(messages, key=lambda x: x['timestamp'])
            recent_messages = sorted_messages[-limit:]
            
            # Calculate wrap width based on Message column width
            message_col_width = self.message_list.column('Message', 'width')
            chars_per_line = message_col_width // 7  # Approximate characters that fit per line
            
            new_selections = []  # Store new item IDs to select
            
            # Add messages to treeview with dynamic word wrapping
            for msg in recent_messages:
                if self.protocol == "custom":
                    timestamp = datetime.fromtimestamp(msg['timestamp'])
                else:
                    timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M:%S')
                content = msg['content']
                
                # Word wrap the content
                words = content.split()
                lines = []
                current_line = []
                current_length = 0
                
                for word in words:
                    word_length = len(word)
                    if current_length + word_length + 1 <= chars_per_line:
                        current_line.append(word)
                        current_length += word_length + 1
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
                        current_length = word_length
                
                if current_line:
                    lines.append(' '.join(current_line))
                
                wrapped_content = '\n'.join(lines)
                
                item_id = self.message_list.insert('', 'end',
                    values=(timestamp, msg['sender'], wrapped_content),
                    tags=('unread' if not msg['is_read'] else 'read',))
                self.message_ids[item_id] = msg['id']
                
                # If this message was previously selected, add it to new selections
                if wrapped_content in selected_contents:
                    new_selections.append(item_id)
            
            # Restore selections
            for item_id in new_selections:
                self.message_list.selection_add(item_id)
            
        except Exception as e:
            logging.error(f"Error refreshing messages: {e}")
            messagebox.showerror("Error", "Failed to refresh messages")
        
    def perform_search(self):
        """Handle search button click"""
        search_text = self.search_entry.get().strip()
        self.current_page = 1  # Reset to first page on new search
        self.update_user_list(search_text)

    def update_user_list(self, search_text=None):
        """Update the user list for the current page"""
        if search_text is None:
            search_text = self.search_entry.get().strip()
        
        self.user_listbox.delete(0, tk.END)  # Always clear first
        
        # Get all accounts
        accounts = self.client.list_accounts(search_text)
        
        if accounts is not None:
            # Filter out current user
            filtered_accounts = [acc for acc in sorted(accounts) 
                               if acc != self.client.current_user]
            
            # Calculate pagination
            start_idx = (self.current_page - 1) * self.page_size
            end_idx = start_idx + self.page_size
            page_accounts = filtered_accounts[start_idx:end_idx]
            
            # Display current page
            for account in page_accounts:
                self.user_listbox.insert(tk.END, account)
            
            # Update page label
            self.page_label.config(text=f"Page {self.current_page}")
            
            # Enable/disable pagination buttons
            self.prev_page_btn.config(state='normal' if self.current_page > 1 else 'disabled')
            self.next_page_btn.config(state='normal' if end_idx < len(filtered_accounts) else 'disabled')

    def next_page(self):
        """Go to next page of results"""
        self.current_page += 1
        self.update_user_list()

    def prev_page(self):
        """Go to previous page of results"""
        if self.current_page > 1:
            self.current_page -= 1
            self.update_user_list()
        
    def mark_selected_read(self):
        """Mark selected messages as read"""
        selected_items = self.message_list.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Please select messages to mark as read")
            return
        
        # Get message IDs for selected items
        message_ids = [self.message_ids[item] for item in selected_items]
        
        if self.client.mark_read(message_ids):
            self.refresh_messages()  # Refresh to update the display
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
            
            if self.client.delete_messages(message_ids):
                messagebox.showinfo("Success", "Messages deleted")
                self.refresh_messages()  # Refresh after deleting
            else:
                messagebox.showerror("Error", "Failed to delete messages")
        
    def show_full_message(self, event):
        """Show the full message in a popup window when double-clicked"""
        selected_items = self.message_list.selection()
        if not selected_items:
            return
        
        # Get the message content
        item = selected_items[0]  # Get first selected item
        values = self.message_list.item(item)['values']
        if not values:
            return
        
        time, sender, content = values

        # marking the message as read
        if self.client.mark_read([self.message_ids[item]]):
            self.refresh_messages()  # Refresh to update the visual state
        else:
            messagebox.showerror("Error", "Failed to mark message as read")
        
        # Create popup window
        popup = tk.Toplevel(self.root)
        popup.title(f"Message from {sender} at {time}")
        popup.geometry("400x300")
        
        # Add text widget with scrollbar
        text_frame = ttk.Frame(popup)
        text_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        text_widget = tk.Text(text_frame, wrap='word', padx=5, pady=5)
        text_widget.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=text_widget.yview)
        scrollbar.pack(side='right', fill='y')
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # Insert message content
        text_widget.insert('1.0', content)
        text_widget.configure(state='disabled')  # Make read-only
        
        # Add close button
        ttk.Button(popup, text="Close", command=popup.destroy).pack(pady=5)
        
        # Make the popup modal
        popup.transient(self.root)
        popup.grab_set()
        self.root.wait_window(popup)
        
    def schedule_refresh(self):
        """Schedule the next auto-refresh"""
        if self.client.current_user and self.notebook.tab(1)['state'] == 'normal':
            self.refresh_messages()
        # Schedule next refresh regardless of current state
        self.root.after(self.refresh_interval, self.schedule_refresh)
        
    def run(self):
        """Start the GUI"""
        self.root.mainloop()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Chat GUI client")
    parser.add_argument("--host", default="localhost", help="Server host")
    args = parser.parse_args()
    
    gui = ChatGUI(host=args.host)
    gui.run()

if __name__ == "__main__":
    main() 