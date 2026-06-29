#!/usr/bin/env python3
"""Extract cookies from Chromium-based browser and output Netscape cookies.txt.
macOS: AES-CBC + PBKDF2 + SHA-256 hash prefix (meta version >= 24).
Usage: python3 extract_cookies.py <profile_path> --browser Dia [--domain DOMAIN]
"""
import sqlite3, os, sys, subprocess, hashlib
from datetime import datetime, timezone
from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes

BROWSER_KEYRING = {
    "Dia": ("Dia", "Dia Safe Storage"),
    "Chrome": ("Chrome", "Chrome Safe Storage"),
    "Chromium": ("Chromium", "Chromium Safe Storage"),
    "Brave": ("Brave", "Brave Safe Storage"),
    "Edge": ("Microsoft Edge", "Microsoft Edge Safe Storage" if sys.platform == "darwin" else "Chromium Safe Storage"),
}

def get_keychain_password(account, service):
    try:
        return subprocess.check_output(
            ["security", "find-generic-password", "-w", "-a", account, "-s", service],
            stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        return None

def derive_key(password_raw, iterations=1003, salt=b'saltysalt', key_length=16):
    return hashlib.pbkdf2_hmac('sha1', password_raw, salt, iterations, key_length)

def aes_cbc_decrypt(ciphertext, key, iv=b' ' * 16):
    c = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = c.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    pad_len = padded[-1]
    return padded[:-pad_len]

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <profile_path> --browser NAME [--domain DOMAIN]", file=sys.stderr)
        print(f"  --browser: Dia, Chrome, Chromium, Brave, Edge", file=sys.stderr)
        sys.exit(1)

    profile_path = os.path.expanduser(sys.argv[1])
    browser_name = None
    domain_filter = None

    for i, arg in enumerate(sys.argv):
        if arg == "--browser" and i + 1 < len(sys.argv):
            browser_name = sys.argv[i + 1]
        if arg == "--domain" and i + 1 < len(sys.argv):
            domain_filter = sys.argv[i + 1]

    if not browser_name:
        print("Error: --browser is required", file=sys.stderr)
        sys.exit(1)

    if browser_name not in BROWSER_KEYRING:
        print(f"Error: unknown browser '{browser_name}'. Options: {', '.join(BROWSER_KEYRING.keys())}", file=sys.stderr)
        sys.exit(1)

    cookies_db = os.path.join(profile_path, "Cookies")
    if not os.path.exists(cookies_db):
        print(f"Error: Cookies database not found at {cookies_db}", file=sys.stderr)
        sys.exit(1)

    account, service = BROWSER_KEYRING[browser_name]
    pw = get_keychain_password(account, service)
    if not pw:
        print(f"Error: No Keychain entry found for {account}/{service}", file=sys.stderr)
        sys.exit(1)

    # yt-dlp uses the raw keychain output (base64 string) directly as PBKDF2 password
    # NOT the base64-decoded bytes
    key = derive_key(pw)
    print(f"# Keychain: {account} / {service}", file=sys.stderr)

    conn = sqlite3.connect(cookies_db)
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM meta WHERE key = 'version'")
    meta_version = int(cursor.fetchone()[0])
    hash_prefix = meta_version >= 24
    print(f"# meta version: {meta_version}, hash_prefix={hash_prefix}", file=sys.stderr)

    query = "SELECT host_key, name, value, path, expires_utc, is_secure, is_httponly, has_expires, encrypted_value FROM cookies"
    params = []
    if domain_filter:
        query += " WHERE host_key LIKE ?"
        params.append(f"%{domain_filter}%")
    cursor.execute(query, params)

    print("# Netscape HTTP Cookie File")
    print(f"# Extracted from: {profile_path} ({browser_name})")
    print(f"# Date: {datetime.now(timezone.utc).isoformat()}")

    count = 0
    for row in cursor.fetchall():
        host_key, name, value, path, expires_utc, is_secure, is_httponly, has_expires, enc_val = row

        if not value and enc_val and enc_val[:3] == b'v10':
            try:
                ciphertext = enc_val[3:]
                plaintext = aes_cbc_decrypt(ciphertext, key)
                if hash_prefix:
                    plaintext = plaintext[32:]
                value = plaintext.decode('utf-8')
            except Exception:
                continue

        if not value:
            continue

        secure = "TRUE" if is_secure else "FALSE"
        domain_specified = "TRUE" if host_key.startswith(".") else "FALSE"
        expires = str(int((expires_utc / 1000000) - 11644473600)) if has_expires else "0"
        print(f"{host_key}\t{domain_specified}\t{path}\t{secure}\t{expires}\t{name}\t{value}")
        count += 1

    conn.close()
    print(f"# Total: {count} cookies", file=sys.stderr)

if __name__ == "__main__":
    main()
