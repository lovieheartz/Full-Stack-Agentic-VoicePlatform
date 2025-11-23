from cryptography.fernet import Fernet
from app.config import settings
import json
import base64


class EncryptionService:
    """Service for encrypting and decrypting sensitive data using Fernet"""

    def __init__(self):
        # Get encryption key from settings
        self.cipher = Fernet(settings.ENCRYPTION_KEY.encode())

    def encrypt_credentials(self, credentials: dict) -> str:
        """
        Encrypt credentials dictionary to string

        Args:
            credentials: Dictionary containing sensitive credentials

        Returns:
            Encrypted string
        """
        # Convert dict to JSON string
        json_str = json.dumps(credentials)

        # Encrypt
        encrypted_bytes = self.cipher.encrypt(json_str.encode())

        # Return as base64 string for storage
        return base64.b64encode(encrypted_bytes).decode()

    def decrypt_credentials(self, encrypted_data: str) -> dict:
        """
        Decrypt encrypted string to credentials dictionary

        Args:
            encrypted_data: Encrypted string from database

        Returns:
            Dictionary containing credentials
        """
        # Decode from base64
        encrypted_bytes = base64.b64decode(encrypted_data.encode())

        # Decrypt
        decrypted_bytes = self.cipher.decrypt(encrypted_bytes)

        # Parse JSON
        return json.loads(decrypted_bytes.decode())


# Singleton instance
encryption_service = EncryptionService()
