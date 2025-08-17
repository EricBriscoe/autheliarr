#!/usr/bin/env python3
"""
Autheliarr - Sync Wizarr users to Authelia
Simple application to ensure all Wizarr users have Authelia accounts
"""

import os
import sqlite3
import yaml
import secrets
import string
import logging
import re
import time
import subprocess
from typing import Dict, List, Optional
from pathlib import Path
from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure secure logger for passwords (writes to separate file if available)
secure_logger = logging.getLogger('autheliarr.secure')
secure_handler = None
try:
    # Try to create secure log file if directory is writable
    secure_log_path = os.getenv('SECURE_LOG_PATH', '/app/secure.log')
    if os.access(os.path.dirname(secure_log_path), os.W_OK):
        secure_handler = logging.FileHandler(secure_log_path, mode='a')
        secure_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        secure_logger.addHandler(secure_handler)
        secure_logger.setLevel(logging.INFO)
        # Don't propagate to root logger to avoid console output
        secure_logger.propagate = False
except (OSError, PermissionError):
    # Fall back to using main logger if secure log unavailable
    pass

class AutheliarrSync:
    def __init__(self):
        self.wizarr_db_path = os.getenv('WIZARR_DB_PATH', '/wizarr/database.db')
        self.authelia_users_path = os.getenv('AUTHELIA_USERS_PATH', '/authelia/users_database.yml')
        self.default_group = os.getenv('DEFAULT_GROUP', 'plex_users')
        self.dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'
        self.sync_interval = int(os.getenv('SYNC_INTERVAL', '0'))  # 0 = run once and exit
        self.authelia_container = os.getenv('AUTHELIA_CONTAINER', 'authelia')
        self.restart_authelia = os.getenv('RESTART_AUTHELIA', 'true').lower() == 'true'
        
    def get_wizarr_users(self) -> List[Dict]:
        """Fetch users from Wizarr database"""
        if not os.path.exists(self.wizarr_db_path):
            logger.error(f"Wizarr database not found at {self.wizarr_db_path}")
            return []
            
        try:
            conn = sqlite3.connect(self.wizarr_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT username, email FROM user WHERE email IS NOT NULL")
            users = [{'username': row[0], 'email': row[1]} for row in cursor.fetchall()]
            conn.close()
            logger.info(f"Found {len(users)} users in Wizarr")
            return users
        except Exception as e:
            logger.error(f"Error reading Wizarr database: {e}")
            return []
    
    def load_authelia_users(self) -> Dict:
        """Load existing Authelia users"""
        if not os.path.exists(self.authelia_users_path):
            logger.warning(f"Authelia users file not found at {self.authelia_users_path}")
            return {'users': {}}
            
        try:
            with open(self.authelia_users_path, 'r') as f:
                data = yaml.safe_load(f)
                return data if data else {'users': {}}
        except Exception as e:
            logger.error(f"Error reading Authelia users file: {e}")
            return {'users': {}}
    
    def restart_authelia_container(self):
        """Restart Authelia container to reload configuration"""
        if self.dry_run:
            logger.info("DRY RUN: Would restart Authelia container")
            return True
            
        if not self.restart_authelia:
            logger.info("Authelia restart disabled, skipping")
            return True
            
        try:
            logger.info(f"Restarting Authelia container: {self.authelia_container}")
            result = subprocess.run(
                ['docker', 'restart', self.authelia_container],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("Authelia container restarted successfully")
                return True
            else:
                logger.error(f"Failed to restart Authelia: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout while restarting Authelia container")
            return False
        except Exception as e:
            logger.error(f"Error restarting Authelia container: {e}")
            return False

    def save_authelia_users(self, users_data: Dict):
        """Save updated Authelia users"""
        if self.dry_run:
            logger.info("DRY RUN: Would save Authelia users file")
            return
            
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.authelia_users_path), exist_ok=True)
            
            with open(self.authelia_users_path, 'w') as f:
                yaml.dump(users_data, f, default_flow_style=False, indent=2)
            logger.info("Updated Authelia users file")
        except Exception as e:
            logger.error(f"Error saving Authelia users file: {e}")
    
    def generate_password(self, length: int = 16) -> str:
        """Generate a cryptographically secure random password"""
        if length < 8:
            length = 8  # Minimum secure length
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def hash_password(self, password: str) -> str:
        """Generate Argon2id hash for password"""
        try:
            # Use Argon2id with Authelia-compatible parameters
            hasher = PasswordHasher(
                memory_cost=65536,  # 64 MB
                time_cost=3,        # 3 iterations
                parallelism=4,      # 4 parallel threads
                hash_len=32,        # 32-byte hash
                salt_len=16         # 16-byte salt
            )
            return hasher.hash(password)
        except Argon2Error as e:
            logger.error(f"Error hashing password: {e}")
            raise
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_username(self, username: str) -> bool:
        """Validate username format"""
        # Alphanumeric plus some safe characters, 3-32 chars
        pattern = r'^[a-zA-Z0-9._-]{3,32}$'
        return re.match(pattern, username) is not None
    
    def _log_password_securely(self, username: str, password: str):
        """Log password with security considerations - always obfuscated in main logs"""
        # Create obfuscated version for main logs
        if len(password) > 6:
            obfuscated = password[:2] + '*' * (len(password) - 4) + password[-2:]
        else:
            obfuscated = '*' * len(password)
        
        # Always log obfuscated version to main log
        logger.warning(f"Generated password for {username}: {obfuscated}")
        
        # Log full password to secure log if available
        if secure_handler and secure_logger.handlers:
            secure_logger.info(f"User: {username} | Password: {password}")
            logger.info(f"Full password for {username} written to secure log: {os.getenv('SECURE_LOG_PATH', '/app/secure.log')}")
        else:
            # No fallback - provide guidance on accessing full passwords
            logger.warning(f"Secure log not configured. Full password not logged anywhere.")
            logger.warning(f"To access full passwords, mount a secure log file with SECURE_LOG_PATH environment variable")
            logger.warning(f"Generated password for {username} must be manually provided to user")
    
    def sync_users(self):
        """Main sync function"""
        logger.info("Starting Autheliarr sync...")
        
        # Get users from both systems
        wizarr_users = self.get_wizarr_users()
        authelia_data = self.load_authelia_users()
        authelia_users = authelia_data.get('users', {})
        
        if not wizarr_users:
            logger.warning("No Wizarr users found, nothing to sync")
            return
        
        # Track changes
        new_users = 0
        updated_users = 0
        
        for wizarr_user in wizarr_users:
            username = wizarr_user['username']
            email = wizarr_user['email']
            
            # Validate user data
            if not self.validate_username(username):
                logger.warning(f"Skipping user {username}: invalid username format")
                continue
                
            if not self.validate_email(email):
                logger.warning(f"Skipping user {username}: invalid email format ({email})")
                continue
            
            if username in authelia_users:
                # User exists, check if email needs updating
                current_email = authelia_users[username].get('email', '')
                if current_email != email:
                    logger.info(f"Updating email for user {username}: {current_email} -> {email}")
                    authelia_users[username]['email'] = email
                    updated_users += 1
                else:
                    logger.debug(f"User {username} already exists with correct email")
            else:
                # Create new user
                password = self.generate_password()
                password_hash = self.hash_password(password)
                
                logger.info(f"Creating new Authelia user: {username} ({email})")
                authelia_users[username] = {
                    'displayname': username.title(),
                    'password': password_hash,
                    'email': email,
                    'groups': [self.default_group]
                }
                new_users += 1
                
                # Log the generated password securely
                self._log_password_securely(username, password)
        
        # Save updated users
        if new_users > 0 or updated_users > 0:
            authelia_data['users'] = authelia_users
            self.save_authelia_users(authelia_data)
            
            # Restart Authelia to reload configuration
            if self.restart_authelia_container():
                logger.info(f"Sync complete: {new_users} new users, {updated_users} updated users")
            else:
                logger.warning(f"Users updated but Authelia restart failed - changes may not be active")
        else:
            logger.info("No changes needed - all users are in sync")

def main():
    """Main entry point"""
    sync = AutheliarrSync()
    
    logger.info(f"Autheliarr starting...")
    logger.info(f"Wizarr DB: {sync.wizarr_db_path}")
    logger.info(f"Authelia Users: {sync.authelia_users_path}")
    logger.info(f"Default Group: {sync.default_group}")
    logger.info(f"Dry Run: {sync.dry_run}")
    logger.info(f"Restart Authelia: {sync.restart_authelia}")
    logger.info(f"Authelia Container: {sync.authelia_container}")
    logger.info(f"Sync Interval: {sync.sync_interval}s ({'periodic' if sync.sync_interval > 0 else 'run once'})")
    
    if sync.sync_interval > 0:
        # Periodic mode
        logger.info(f"Running in periodic mode - syncing every {sync.sync_interval} seconds")
        
        while True:
            try:
                sync.sync_users()
                if sync.sync_interval > 0:
                    logger.info(f"Waiting {sync.sync_interval} seconds until next sync...")
                    time.sleep(sync.sync_interval)
                else:
                    break
            except KeyboardInterrupt:
                logger.info("Shutting down gracefully...")
                break
            except Exception as e:
                logger.error(f"Sync failed: {e}")
                if sync.sync_interval > 0:
                    logger.info(f"Retrying in {sync.sync_interval} seconds...")
                    time.sleep(sync.sync_interval)
                else:
                    exit(1)
    else:
        # Single run mode
        try:
            sync.sync_users()
            logger.info("Autheliarr finished successfully")
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            exit(1)

if __name__ == "__main__":
    main()