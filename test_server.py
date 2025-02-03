"""
Chat Server Tests

This module contains unit tests for the chat server functionality,
focusing on user authentication and account management.
"""

import unittest
from server import ChatServer, User
import os

class TestChatServer(unittest.TestCase):
    """Test cases for the ChatServer class"""
    
    def setUp(self):
        """Set up a fresh server instance for each test"""
        self.server = ChatServer()
        self.test_username = "testuser"
        self.test_password = "testpass123"
    
    def test_password_hashing(self):
        """Test that password hashing is consistent and secure"""
        # Test with fixed salt
        salt = os.urandom(32)
        hash1, _ = self.server.hash_password(self.test_password, salt)
        hash2, _ = self.server.hash_password(self.test_password, salt)
        
        # Same password + same salt should yield same hash
        self.assertEqual(hash1, hash2)
        
        # Different salts should yield different hashes
        hash3, salt2 = self.server.hash_password(self.test_password) # returns a tuple of the hash and the generated salt
        self.assertNotEqual(salt, salt2)
        self.assertNotEqual(hash1, hash3)
    
    def test_account_creation(self):
        """Test account creation functionality"""
        # Test successful account creation
        self.assertTrue(
            self.server.create_account(self.test_username, self.test_password)
        )
        
        # Verify user exists
        self.assertIn(self.test_username, self.server.users)
        
        # Test duplicate username
        self.assertFalse(
            self.server.create_account(self.test_username, "different_password")
        )
        
        # Verify user data
        user = self.server.users[self.test_username]
        self.assertIsInstance(user, User)
        self.assertEqual(user.username, self.test_username)
        self.assertFalse(user.is_online)
    
    def test_authentication(self):
        """Test user authentication"""
        # Create test account
        self.server.create_account(self.test_username, self.test_password)
        
        # Test successful authentication
        self.assertTrue(
            self.server.authenticate(self.test_username, self.test_password)
        )
        
        # Test wrong password
        self.assertFalse(
            self.server.authenticate(self.test_username, "wrongpass")
        )
        
        # Test non-existent user
        self.assertFalse(
            self.server.authenticate("nonexistent", self.test_password)
        )
    
    def test_password_security(self):
        """Test password security requirements"""
        # Create account with test password
        self.server.create_account(self.test_username, self.test_password)
        user = self.server.users[self.test_username]
        
        # Verify salt and hash are different
        self.assertNotEqual(user.password_hash, self.test_password.encode())
        self.assertNotEqual(user.salt, self.test_password.encode())
        
        # Verify salt length (should be 32 bytes)
        self.assertEqual(len(user.salt), 32)
        
        # Verify hash length (should be 32 bytes for SHA256)
        self.assertEqual(len(user.password_hash), 32)

class TestChatServerConcurrency(unittest.TestCase):
    """Test cases for concurrent operations on the ChatServer"""
    
    def setUp(self):
        self.server = ChatServer()
    
    def test_multiple_accounts(self):
        """Test handling multiple user accounts"""
        # Create multiple accounts
        usernames = [f"user{i}" for i in range(100)]
        passwords = [f"pass{i}" for i in range(100)]
        
        # Create all accounts
        for username, password in zip(usernames, passwords):
            self.assertTrue(
                self.server.create_account(username, password)
            )
        
        # Verify all accounts exist
        self.assertEqual(len(self.server.users), 100)
        
        # Verify all accounts can authenticate
        for username, password in zip(usernames, passwords):
            self.assertTrue(
                self.server.authenticate(username, password)
            )

if __name__ == '__main__':
    unittest.main(verbosity=2) 