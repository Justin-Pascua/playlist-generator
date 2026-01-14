from pwdlib import PasswordHash
pwd_hash = PasswordHash.recommended()

def hash(password: str):
    return pwd_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_hash.verify(plain_password, hashed_password)

    