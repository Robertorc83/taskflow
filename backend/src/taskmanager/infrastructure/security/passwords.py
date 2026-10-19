from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._hash = PasswordHash((Argon2Hasher(),))

    def hash(self, password: str) -> str:
        return self._hash.hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        return self._hash.verify(password, hashed)
