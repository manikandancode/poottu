# src/poottu/core/encryption.py

import os
from nacl.bindings import (
    crypto_aead_xchacha20poly1305_ietf_encrypt,
    crypto_aead_xchacha20poly1305_ietf_decrypt,
)
from nacl.hash import blake2b
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


def encrypt(key, plaintext):
    if not plaintext:
        return None
    nonce = os.urandom(24)
    ciphertext = crypto_aead_xchacha20poly1305_ietf_encrypt(
        message=plaintext.encode('utf-8'),
        aad=None,
        nonce=nonce,
        key=key
    )
    return nonce + ciphertext


def decrypt(key, data):
    if not data:
        return ""
    nonce = data[:24]
    ciphertext = data[24:]
    plaintext = crypto_aead_xchacha20poly1305_ietf_decrypt(
        ciphertext=ciphertext,
        aad=None,
        nonce=nonce,
        key=key
    )
    return plaintext.decode('utf-8')


def blind_index(key, text):
    index_key = derive_blind_key(key)
    h = blake2b(text.encode('utf-8'), key=index_key, digest_size=16)
    return h.hex()


def derive_blind_key(key):
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"poottu_blind_index"
    )
    return hkdf.derive(key)
