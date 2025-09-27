# src/poottu/core/vault.py

import json
import base64
import os
import hmac
import hashlib
from argon2 import low_level as argon2

class Vault:
    VERSION = "1.0"
    KDF = "argon2id"
    DEFAULT_PARAMS = {
        "time_cost": 4,
        "memory_cost": 65536,
        "parallelism": 1,
        "hash_len": 32
    }

    @classmethod
    def create(cls, master_password, header_path):
        salt = os.urandom(16)
        header = {
            "version": cls.VERSION,
            "kdf": cls.KDF,
            "salt": base64.b64encode(salt).decode('utf-8'),
            "params": cls.DEFAULT_PARAMS
        }
        key = argon2.hash_secret_raw(
            secret=master_password.encode('utf-8'),
            salt=salt,
            time_cost=cls.DEFAULT_PARAMS["time_cost"],
            memory_cost=cls.DEFAULT_PARAMS["memory_cost"],
            parallelism=cls.DEFAULT_PARAMS["parallelism"],
            hash_len=cls.DEFAULT_PARAMS["hash_len"],
            type=argon2.Type.ID
        )
        json_str = json.dumps(header, separators=(',', ':'), sort_keys=True)
        mac = hmac.new(key, json_str.encode('utf-8'), hashlib.sha256).digest()
        header["mac"] = base64.b64encode(mac).decode('utf-8')

        # Base64-encode the entire header for obfuscation (not encryption)
        obfuscated_header = base64.b64encode(json.dumps(header).encode('utf-8')).decode('utf-8')

        os.makedirs(os.path.dirname(header_path), exist_ok=True)
        with open(header_path, 'w') as f:
            f.write(obfuscated_header)
        return key

    @classmethod
    def load(cls, master_password, header_path):
        with open(header_path, 'r') as f:
            obfuscated_header = f.read()

        # Decode the base64 obfuscation
        try:
            header_json = base64.b64decode(obfuscated_header).decode('utf-8')
            header = json.loads(header_json)
        except (base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError("Corrupted header file")

        if header["version"] != cls.VERSION:
            raise ValueError("Unsupported vault version")
        params = header["params"]
        salt = base64.b64decode(header["salt"])
        key = argon2.hash_secret_raw(
            secret=master_password.encode('utf-8'),
            salt=salt,
            time_cost=params["time_cost"],
            memory_cost=params["memory_cost"],
            parallelism=params["parallelism"],
            hash_len=params["hash_len"],
            type=argon2.Type.ID
        )
        header_no_mac = {k: v for k, v in header.items() if k != "mac"}
        json_str = json.dumps(header_no_mac, separators=(',', ':'), sort_keys=True)
        computed_mac = hmac.new(key, json_str.encode('utf-8'), hashlib.sha256).digest()
        stored_mac = base64.b64decode(header["mac"])
        if not hmac.compare_digest(computed_mac, stored_mac):
            raise ValueError("Invalid master password")
        return key
