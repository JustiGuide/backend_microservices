import json
import os
import base64
from typing import Any, Union
from cryptography.hazmat.primitives.ciphers.aead import AESSIV
from cryptography.exceptions import InvalidTag
from passlib.context import CryptContext
from dotenv import load_dotenv
from nanoid import generate
from sqlalchemy import Text, TypeDecorator

load_dotenv()


class Encrypt:
    def __init__(self):
        self.ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
        self.key = base64.urlsafe_b64decode(self.ENCRYPTION_KEY)
        self.encryptor = AESSIV(self.key)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.aad = [
            b"authenticated but unencrypted data",
            b"W\xd6!\xf2\xc68\x99\xb97\x00Y\x02fr\xacE\xb83\x1c\xfe\x0e\x8c\xed:g\x18\xd1\x84\x876\x06\x9a",
        ]

    def encrypt_data(self, data: Union[dict, list, str, Any]) -> str:
        if data is None:
            return None
        try:
            if isinstance(data, dict) or isinstance(data, list):
                data_bytes = json.dumps(data).encode("utf-8")
            else:
                data_bytes = str(data).encode("utf-8")
            encrypted_bytes = self.encryptor.encrypt(data_bytes, self.aad)
            return base64.urlsafe_b64encode(encrypted_bytes).decode("utf-8")
        except Exception as e:
            print(f"Encryption failed: {e}")
            return None

    def encrypt_bytes(self, data: bytes) -> str:
        if data is None and not isinstance(data, bytes):
            return None
        try:
            encrypted_bytes = self.encryptor.encrypt(data, self.aad)
            return base64.urlsafe_b64encode(encrypted_bytes).decode("utf-8")
        except Exception as e:
            print(f"Encryption failed: {e}")
            return None

    def decrypt_data(self, encrypted_data_b64: str) -> Union[dict, list, str, None]:
        if encrypted_data_b64 is None:
            return None
        try:
            encrypted_bytes = base64.urlsafe_b64decode(
                encrypted_data_b64.encode("utf-8")
            )
            decrypted_bytes = self.encryptor.decrypt(encrypted_bytes, self.aad)
            decrypted_string = decrypted_bytes.decode("utf-8")
            try:
                return json.loads(decrypted_string)
            except json.JSONDecodeError:
                return decrypted_string
        except InvalidTag:
            print("Decryption failed: Invalid token or key")
            return None
        except Exception as e:
            print(f"Decryption failed: {e}")
            return None

    def decrypt_bytes(self, encrypted_data_b64: str) -> bytes:
        if encrypted_data_b64 is None:
            return None
        try:
            encrypted_bytes = base64.urlsafe_b64decode(
                encrypted_data_b64.encode("utf-8")
            )
            decrypted_bytes = self.encryptor.decrypt(encrypted_bytes, self.aad)
            return decrypted_bytes
        except InvalidTag:
            print("Decryption failed: Invalid token or key")
            return None
        except Exception as e:
            print(f"Decryption failed: {e}")
            return None

    def hash_password(self, password: str) -> str:
        if password is not None:
            return self.pwd_context.hash(password)
        return None

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        if hashed_password is None:
            return False
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            print(f"Password verification error: {e}")
            return False

    @staticmethod
    def generate_uuid():
        return generate("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", 7)


class EncryptedText(TypeDecorator):
    impl = Text
    cache_ok = True
    encr = Encrypt()

    def process_bind_param(self, value, dialect):
        if value is not None:
            return self.encr.encrypt_data(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return self.encr.decrypt_data(value)
        return None


class EncryptedBytes(TypeDecorator):
    impl = Text
    cache_ok = True
    encr = Encrypt()

    def process_bind_param(self, value, dialect):
        if value is not None:
            return self.encr.encrypt_bytes(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return self.encr.decrypt_bytes(value)
        return None

    @property
    def python_type(self):
        return bytes
