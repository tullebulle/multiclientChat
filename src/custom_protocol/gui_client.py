"""
GUI Client for Custom Protocol Chat

A graphical interface using tkinter for the chat client.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from src.custom_protocol import protocol
from .client import CustomChatClient
import argparse

class ChatGUI:
    def __init__(self, host="localhost", port=9999):
        self.client = CustomChatClient(host=host, port=port)
        if not self.client.connect():
            messagebox.showerror("Error", "Could not connect to server!")
            return
        
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
        
        # Top frame for user info and refresh
        top_frame = ttk.Frame(frame)
        top_frame.pack(fill='x', padx=5, pady=5)
        
        # User info and refresh button side by side
        self.login_label = ttk.Label(top_frame, text="Not logged in", font=('TkDefaultFont', 10, 'bold'))
        self.login_label.pack(side='left', anchor='w')
        
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
        
        self.message_list.column('Time', width=70, anchor='w')
        self.message_list.column('From', width=100, anchor='w')
        self.message_list.column('Message', width=300, anchor='w')
        
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
            
        if self.client.login(username, password):
            messagebox.showinfo("Success", "Logged in successfully!")
            self.notebook.tab(1, state='normal')
            self.notebook.select(1)
            self.login_label.config(text=f"Logged in as: {username}")
            self.search_entry.delete(0, tk.END)
            self.perform_search()
            self.refresh_messages()  # Initial message load
        else:
            messagebox.showerror("Error", "Login failed")
            
    def handle_register(self):
        """Handle registration button click"""
        username = self.reg_username.get().strip()
        password = self.reg_password.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
            
        if self.client.create_account(username, password):
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
        
        # Check for unread messages
        if self.client.current_user == username:
            messages = self.client.get_messages(include_read=False)
            if messages:
                if not messagebox.askyesno("Warning", 
                                         f"You have {len(messages)} unread messages!\n"
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
        """Manually refresh messages"""
        if not self.client.current_user:
            return
        
        try:
            messages = self.client.get_messages(include_read=True)
            
            # Clear existing messages
            for item in self.message_list.get_children():
                self.message_list.delete(item)
            self.message_ids.clear()
            
            # Add messages to treeview
            for msg in sorted(messages, key=lambda x: x['timestamp']):
                timestamp = msg['timestamp'].strftime('%H:%M:%S')
                item_id = self.message_list.insert('', 'end',
                    values=(timestamp, msg['sender'], msg['content']),
                    tags=('unread' if not msg['is_read'] else 'read',))
                self.message_ids[item_id] = msg['id']
                
        except Exception as e:
            logging.error(f"Error refreshing messages: {e}")
            messagebox.showerror("Error", "Failed to refresh messages")
        
    def perform_search(self):
        """Handle search button click"""
        search_text = self.search_entry.get().strip()
        
        self.user_listbox.delete(0, tk.END)  # Always clear first
        
        accounts = self.client.list_accounts(search_text)  # No need for wildcards anymore
        if accounts is not None:  # Check for None instead of truthiness
            for account in sorted(accounts):
                if account != self.client.current_user:  # Don't show current user
                    self.user_listbox.insert(tk.END, account)
        
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