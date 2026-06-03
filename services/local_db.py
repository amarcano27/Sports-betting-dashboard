"""
SQLite compatibility layer — mirrors the Supabase Python client interface
so all existing code works unchanged when no SUPABASE_URL is configured.

Supported patterns:
    db.table("t").select("*").eq("col", val).order("col").limit(n).execute().data
    db.table("t").insert([{...}]).execute()
    db.table("t").upsert([{...}], on_conflict="col").execute()
    db.table("t").update({...}).eq("col", val).execute()
    db.table("t").delete().eq("col", val).execute()
"""
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import local

DB_PATH = Path(__file__).parent.parent / "data" / "local.db"
DB_PATH.parent.mkdir(exist_ok=True)

_thread_local = local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_thread_local, "conn"):
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _thread_local.conn = conn
    return _thread_local.conn


def _new_id() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_db(val):
    """Convert Python value → SQLite-safe value."""
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    return val


def _from_row(row: sqlite3.Row) -> dict:
    """Convert sqlite3.Row → plain dict, decoding JSON strings."""
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, str) and v and v[0] in ("{", "["):
            try:
                d[k] = json.loads(v)
            except Exception:
                pass
    return d


class _Result:
    def __init__(self, data):
        self.data = data


class _QueryBuilder:
    def __init__(self, table: str, conn: sqlite3.Connection):
        self._table = table
        self._conn = conn
        self._select_cols = "*"
        self._filters: list[tuple] = []
        self._in_filters: list[tuple] = []
        self._order: list[str] = []
        self._limit_val: int | None = None
        self._action = "select"
        self._payload = None
        self._upsert_conflict: str | None = None
        self._update_data: dict | None = None

    # ── filtering ────────────────────────────────────────────────
    def select(self, cols="*"):
        self._select_cols = cols
        return self

    def eq(self, col, val):
        # Handle joined table references like "players.sport"
        col = col.split(".")[-1]
        self._filters.append((col, "=", val))
        return self

    def in_(self, col, values):
        col = col.split(".")[-1]
        self._in_filters.append((col, values))
        return self

    def neq(self, col, val):
        col = col.split(".")[-1]
        self._filters.append((col, "!=", val))
        return self

    def gte(self, col, val):
        col = col.split(".")[-1]
        self._filters.append((col, ">=", val))
        return self

    def lte(self, col, val):
        col = col.split(".")[-1]
        self._filters.append((col, "<=", val))
        return self

    def order(self, col, desc=False):
        direction = "DESC" if desc else "ASC"
        self._order.append(f"{col.split('.')[-1]} {direction}")
        return self

    def limit(self, n):
        self._limit_val = n
        return self

    # ── mutations ────────────────────────────────────────────────
    def insert(self, rows):
        self._action = "insert"
        self._payload = rows if isinstance(rows, list) else [rows]
        return self

    def upsert(self, rows, on_conflict=None):
        self._action = "upsert"
        self._payload = rows if isinstance(rows, list) else [rows]
        self._upsert_conflict = on_conflict
        return self

    def update(self, data):
        self._action = "update"
        self._update_data = data
        return self

    def delete(self):
        self._action = "delete"
        return self

    # ── build WHERE clause ───────────────────────────────────────
    def _where(self):
        clauses, params = [], []
        for col, op, val in self._filters:
            clauses.append(f"{col} {op} ?")
            params.append(val)
        for col, values in self._in_filters:
            placeholders = ",".join("?" * len(values))
            clauses.append(f"{col} IN ({placeholders})")
            params.extend(values)
        sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        return sql, params

    # ── execute ──────────────────────────────────────────────────
    def execute(self) -> _Result:
        conn = self._conn
        if self._action == "select":
            return self._do_select(conn)
        elif self._action == "insert":
            return self._do_insert(conn)
        elif self._action == "upsert":
            return self._do_upsert(conn)
        elif self._action == "update":
            return self._do_update(conn)
        elif self._action == "delete":
            return self._do_delete(conn)
        return _Result([])

    def _do_select(self, conn):
        # Resolve column names (strip join prefixes, handle *)
        cols = self._select_cols
        if cols == "*":
            col_sql = "*"
        else:
            cleaned = [c.split("(")[0].split("!")[-1].strip() for c in cols.split(",")]
            col_sql = ", ".join(cleaned)

        where_sql, params = self._where()
        order_sql = (" ORDER BY " + ", ".join(self._order)) if self._order else ""
        limit_sql = f" LIMIT {self._limit_val}" if self._limit_val else ""

        sql = f"SELECT {col_sql} FROM {self._table}{where_sql}{order_sql}{limit_sql}"
        try:
            cursor = conn.execute(sql, params)
            rows = [_from_row(r) for r in cursor.fetchall()]
        except sqlite3.OperationalError:
            rows = []
        return _Result(rows)

    def _do_insert(self, conn):
        inserted = []
        for row in self._payload:
            row = dict(row)
            if "id" not in row or not row["id"]:
                row["id"] = _new_id()
            if "created_at" not in row:
                row["created_at"] = _now_iso()
            cols = list(row.keys())
            placeholders = ",".join("?" * len(cols))
            vals = [_to_db(row[c]) for c in cols]
            sql = f"INSERT OR IGNORE INTO {self._table} ({','.join(cols)}) VALUES ({placeholders})"
            try:
                conn.execute(sql, vals)
                conn.commit()
                inserted.append(row)
            except Exception as e:
                print(f"[local_db] insert error: {e}")
        return _Result(inserted)

    def _do_upsert(self, conn):
        upserted = []
        conflict_col = self._upsert_conflict or "id"
        for row in self._payload:
            row = dict(row)
            if "id" not in row or not row["id"]:
                row["id"] = _new_id()
            if "created_at" not in row:
                row["created_at"] = _now_iso()
            cols = list(row.keys())
            placeholders = ",".join("?" * len(cols))
            vals = [_to_db(row[c]) for c in cols]
            updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c != conflict_col)
            sql = (
                f"INSERT INTO {self._table} ({','.join(cols)}) VALUES ({placeholders}) "
                f"ON CONFLICT({conflict_col}) DO UPDATE SET {updates}"
            )
            try:
                conn.execute(sql, vals)
                conn.commit()
                upserted.append(row)
            except Exception as e:
                print(f"[local_db] upsert error: {e}")
        return _Result(upserted)

    def _do_update(self, conn):
        data = {k: _to_db(v) for k, v in self._update_data.items()}
        data["updated_at"] = _now_iso()
        set_clause = ", ".join(f"{k}=?" for k in data.keys())
        where_sql, where_params = self._where()
        sql = f"UPDATE {self._table} SET {set_clause}{where_sql}"
        params = list(data.values()) + where_params
        try:
            conn.execute(sql, params)
            conn.commit()
        except Exception as e:
            print(f"[local_db] update error: {e}")
        return _Result([])

    def _do_delete(self, conn):
        where_sql, params = self._where()
        sql = f"DELETE FROM {self._table}{where_sql}"
        try:
            conn.execute(sql, params)
            conn.commit()
        except Exception as e:
            print(f"[local_db] delete error: {e}")
        return _Result([])


class LocalDB:
    """Drop-in replacement for the Supabase client."""

    def __init__(self):
        self._conn = _get_conn()
        self._init_schema()

    def table(self, name: str) -> _QueryBuilder:
        return _QueryBuilder(name, self._conn)

    def _init_schema(self):
        stmts = [
            """CREATE TABLE IF NOT EXISTS games (
                id TEXT PRIMARY KEY,
                sport TEXT,
                external_id TEXT UNIQUE,
                home_team TEXT,
                away_team TEXT,
                start_time TEXT,
                status TEXT DEFAULT 'scheduled',
                created_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS odds_snapshots (
                id TEXT PRIMARY KEY,
                game_id TEXT,
                book TEXT,
                market_type TEXT,
                market_label TEXT,
                line REAL,
                price REAL,
                raw TEXT,
                created_at TEXT,
                FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY,
                external_id TEXT UNIQUE,
                name TEXT NOT NULL,
                position TEXT,
                team TEXT,
                sport TEXT,
                jersey_number INTEGER,
                height TEXT,
                weight INTEGER,
                birth_date TEXT,
                raw_data TEXT,
                created_at TEXT,
                updated_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS player_game_stats (
                id TEXT PRIMARY KEY,
                player_id TEXT,
                game_id TEXT,
                date TEXT NOT NULL,
                opponent TEXT,
                home INTEGER DEFAULT 1,
                minutes_played REAL,
                points INTEGER,
                rebounds INTEGER,
                assists INTEGER,
                steals INTEGER,
                blocks INTEGER,
                turnovers INTEGER,
                field_goals_made INTEGER,
                field_goals_attempted INTEGER,
                three_pointers_made INTEGER,
                three_pointers_attempted INTEGER,
                free_throws_made INTEGER,
                free_throws_attempted INTEGER,
                raw_data TEXT,
                created_at TEXT,
                UNIQUE(player_id, game_id),
                FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE,
                FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS player_prop_odds (
                id TEXT PRIMARY KEY,
                player_id TEXT,
                game_id TEXT,
                book TEXT,
                prop_type TEXT,
                line REAL,
                over_price REAL,
                under_price REAL,
                raw TEXT,
                created_at TEXT,
                FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE,
                FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS ai_suggestions (
                id TEXT PRIMARY KEY,
                legs TEXT,
                total_odds REAL,
                ev_score REAL,
                rationale TEXT,
                created_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS player_injuries (
                id TEXT PRIMARY KEY,
                player_id TEXT,
                injury_type TEXT,
                severity TEXT,
                impact_percentage REAL,
                status TEXT DEFAULT 'active',
                expected_return_date TEXT,
                updated_at TEXT,
                created_at TEXT,
                FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS prop_feed_snapshots (
                id TEXT PRIMARY KEY,
                player_id TEXT,
                game_id TEXT,
                sport TEXT,
                prop_type TEXT,
                line REAL,
                book TEXT,
                over_price REAL,
                under_price REAL,
                projection REAL,
                edge REAL,
                hit_rate REAL,
                metadata TEXT,
                snapshot_at TEXT,
                created_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS dfs_lines (
                id TEXT PRIMARY KEY,
                player_id TEXT,
                prop_type TEXT,
                line REAL,
                side TEXT,
                source TEXT,
                game_id TEXT,
                created_at TEXT
            )""",
            # Indexes
            "CREATE INDEX IF NOT EXISTS idx_games_sport ON games(sport)",
            "CREATE INDEX IF NOT EXISTS idx_odds_game ON odds_snapshots(game_id)",
            "CREATE INDEX IF NOT EXISTS idx_players_sport ON players(sport)",
            "CREATE INDEX IF NOT EXISTS idx_props_player ON player_prop_odds(player_id)",
            "CREATE INDEX IF NOT EXISTS idx_feed_sport ON prop_feed_snapshots(sport)",
            "CREATE INDEX IF NOT EXISTS idx_stats_player ON player_game_stats(player_id)",
        ]
        for stmt in stmts:
            try:
                self._conn.execute(stmt)
            except Exception as e:
                print(f"[local_db] schema error: {e}")
        self._conn.commit()
