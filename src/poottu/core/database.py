# src/poottu/core/database.py

import sqlite3
from datetime import datetime
from poottu.core.encryption import encrypt, decrypt, blind_index

class Database:
    def __init__(self, db_path, key):
        self.db_path = db_path
        self.key = key
        self.conn = sqlite3.connect(db_path)
        self.init_tables()

    def init_tables(self):
        cur = self.conn.cursor()

        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_enc BLOB NOT NULL,
                name_index TEXT UNIQUE NOT NULL,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        
        gen_idx = blind_index(self.key, "general")
        cur.execute("SELECT id FROM groups WHERE name_index = ?", (gen_idx,))
        if cur.fetchone() is None:
            gen_enc = encrypt(self.key, "General")
            cur.execute("INSERT INTO groups (name_enc, name_index) VALUES (?, ?)", (gen_enc, gen_idx))

        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                title_enc BLOB NOT NULL,
                username_enc BLOB NOT NULL,
                password_enc BLOB NOT NULL,
                old_password_enc BLOB,
                url_enc BLOB,
                notes_enc BLOB,
                expires TIMESTAMP,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                title_index TEXT NOT NULL,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE SET NULL
            )
        """)

        self.conn.commit()

    
    def add_group(self, name):
        cur = self.conn.cursor()
        norm = (name or "").strip().lower()
        name_enc = encrypt(self.key, name or "")
        name_idx = blind_index(self.key, norm)
        
        cur.execute("INSERT OR IGNORE INTO groups (name_enc, name_index) VALUES (?, ?)", (name_enc, name_idx))
        cur.execute("UPDATE groups SET name_enc = ?, modified = CURRENT_TIMESTAMP WHERE name_index = ?", (name_enc, name_idx))
        self.conn.commit()

    def edit_group(self, old_name, new_name):
        cur = self.conn.cursor()
        old_idx = blind_index(self.key, (old_name or "").strip().lower())
        new_idx = blind_index(self.key, (new_name or "").strip().lower())
        new_enc = encrypt(self.key, new_name or "")
        
        cur.execute("""
            UPDATE groups
            SET name_enc = ?, name_index = ?, modified = CURRENT_TIMESTAMP
            WHERE name_index = ?
        """, (new_enc, new_idx, old_idx))
        
        self.conn.commit()

    def delete_group(self, name):
        cur = self.conn.cursor()
        
        gen_idx = blind_index(self.key, "general")
        cur.execute("SELECT id FROM groups WHERE name_index = ?", (gen_idx,))
        row = cur.fetchone()
        if row is None:
            
            self.add_group("General")
            cur.execute("SELECT id FROM groups WHERE name_index = ?", (gen_idx,))
            row = cur.fetchone()
        general_id = row[0]

        del_idx = blind_index(self.key, (name or "").strip().lower())
        cur.execute("SELECT id FROM groups WHERE name_index = ?", (del_idx,))
        victim = cur.fetchone()
        if victim:
            gid = victim[0]
            cur.execute("UPDATE entries SET group_id = ? WHERE group_id = ?", (general_id, gid))
            cur.execute("DELETE FROM groups WHERE id = ?", (gid,))
            self.conn.commit()

    def get_groups(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, name_enc FROM groups")
        rows = cur.fetchall()
        result = []
        for gid, name_enc in rows:
            name = decrypt(self.key, name_enc)
            result.append({"id": gid, "name": name})
        return result

    
    def add_entry(self, **kwargs):
        group_name = kwargs.pop('group')
        cur = self.conn.cursor()

        
        norm = (group_name or "").strip().lower()
        gidx = blind_index(self.key, norm)
        cur.execute("SELECT id FROM groups WHERE name_index = ?", (gidx,))
        group_row = cur.fetchone()
        if not group_row:
            raise ValueError(f"Group {group_name} does not exist")
        group_id = group_row[0]

        title = kwargs.get('title', '')
        username = kwargs.get('username', '')
        password = kwargs.get('password', '')
        old_password = kwargs.get('old_password', '')
        url = kwargs.get('url', '')
        notes = kwargs.get('notes', '')
        expires = kwargs.get('expires', None)

        title_enc = encrypt(self.key, title)
        username_enc = encrypt(self.key, username)
        password_enc = encrypt(self.key, password)
        old_password_enc = encrypt(self.key, old_password) if old_password else None
        url_enc = encrypt(self.key, url) if url else None
        notes_enc = encrypt(self.key, notes) if notes else None
        title_index = blind_index(self.key, title)

        cur.execute("""
            INSERT INTO entries (group_id, title_enc, username_enc, password_enc, old_password_enc, url_enc, notes_enc, expires, created, modified, title_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?)
        """, (group_id, title_enc, username_enc, password_enc, old_password_enc, url_enc, notes_enc, expires, title_index))

        self.conn.commit()
        return cur.lastrowid

    def update_entry(self, entry_id, **kwargs):
        group_name = kwargs.get('group')
        cur = self.conn.cursor()

        norm = (group_name or "").strip().lower()
        gidx = blind_index(self.key, norm)
        cur.execute("SELECT id FROM groups WHERE name_index = ?", (gidx,))
        group_row = cur.fetchone()
        if not group_row:
            raise ValueError(f"Group {group_name} does not exist")
        group_id = group_row[0]

        title = kwargs.get('title', '')
        username = kwargs.get('username', '')
        password = kwargs.get('password', '')
        old_password = kwargs.get('old_password', '')
        url = kwargs.get('url', '')
        notes = kwargs.get('notes', '')
        expires = kwargs.get('expires', None)

        title_enc = encrypt(self.key, title)
        username_enc = encrypt(self.key, username)
        password_enc = encrypt(self.key, password)
        old_password_enc = encrypt(self.key, old_password) if old_password else None
        url_enc = encrypt(self.key, url) if url else None
        notes_enc = encrypt(self.key, notes) if notes else None
        title_index = blind_index(self.key, title)

        cur.execute("""
            UPDATE entries SET
                group_id = ?, title_enc = ?, username_enc = ?, password_enc = ?, old_password_enc = ?,
                url_enc = ?, notes_enc = ?, expires = ?, modified = CURRENT_TIMESTAMP, title_index = ?
            WHERE id = ?
        """, (group_id, title_enc, username_enc, password_enc, old_password_enc, url_enc, notes_enc, expires, title_index, entry_id))

        self.conn.commit()

    def delete_entry(self, entry_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        self.conn.commit()

    def get_entry(self, entry_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        row = cur.fetchone()
        if row:
            return self.decrypt_row(row)
        return None

    def get_entries(self, search_term=None):
        cur = self.conn.cursor()
        if search_term:
            idx = blind_index(self.key, search_term)
            cur.execute("SELECT * FROM entries WHERE title_index = ?", (idx,))
        else:
            cur.execute("SELECT * FROM entries")
        rows = cur.fetchall()
        return [self.decrypt_row(row) for row in rows]

    def get_entries_by_group(self, group_name):
        cur = self.conn.cursor()
        norm = (group_name or "").strip().lower()
        gidx = blind_index(self.key, norm)
        cur.execute("SELECT id FROM groups WHERE name_index = ?", (gidx,))
        row = cur.fetchone()
        if not row:
            return []
        group_id = row[0]
        cur.execute("SELECT * FROM entries WHERE group_id = ?", (group_id,))
        rows = cur.fetchall()
        return [self.decrypt_row(row) for row in rows]

    def decrypt_row(self, row):
        id_ = row[0]
        group_id = row[1]
        title_enc = row[2]
        username_enc = row[3]
        password_enc = row[4]
        old_password_enc = row[5]
        url_enc = row[6]
        notes_enc = row[7]
        expires = row[8]
        created = row[9]
        modified = row[10]
        title_idx = row[11]

        title = decrypt(self.key, title_enc)
        username = decrypt(self.key, username_enc)
        password = decrypt(self.key, password_enc)
        old_password = decrypt(self.key, old_password_enc) if old_password_enc else ""
        url = decrypt(self.key, url_enc) if url_enc else ""
        notes = decrypt(self.key, notes_enc) if notes_enc else ""

        return {
            "id": id_,
            "group_id": group_id,
            "title": title,
            "username": username,
            "password": password,
            "old_password": old_password,
            "url": url,
            "notes": notes,
            "expires": expires,
            "created": created,
            "modified": modified
        }

    def close(self):
        self.conn.close()
