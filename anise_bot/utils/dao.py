import sqlite3

from anise_core import DATA_PATH

DB_PATH = DATA_PATH / 'count_limiter.db'


class CountLimiterDao:

    def __init__(self, name, path=DB_PATH):
        self.db_path: str = path
        self.gacha_daily_limit: str = name
        self._create_table()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        conn = self._connect()
        conn.execute(f'''
        CREATE TABLE IF NOT EXISTS {self.gacha_daily_limit}
        (
        uid     INTEGER     NOT NULL,
        today   DATETIME    NOT NULL,
        count   INTEGER     NOT NULL,
        PRIMARY KEY(uid)
        )
        '''.strip())
        conn.commit()
        conn.close()

    def read_gacha_all(self):
        conn = self._connect()
        r = conn.execute(f'SELECT * FROM {self.gacha_daily_limit}').fetchall()
        return r

    def read_gacha_record(self, uid):
        conn = self._connect()
        r = conn.execute(f'SELECT * FROM {self.gacha_daily_limit} WHERE uid=?', (uid,)).fetchall()
        return r

    def write_gacha_record(self, uid, today, count):
        conn = self._connect()
        conn.execute(
            f'INSERT OR REPLACE INTO {self.gacha_daily_limit} (uid, today, count) VALUES (?, ?, ?)',
            (uid, today, count))
        conn.commit()
        conn.close()
