"""
Database connection, schema init, and CRUD helpers.
Each public function opens/closes its own connection – no shared state.
"""
import sqlite3

from config import DB_PATH, DATA_DIR, DEFAULT_DESCRIPTIONS


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _row(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


def _phone_row(row: sqlite3.Row) -> dict:
    """Convert a phone row: cast ois to bool, add is_reference=False."""
    d = _row(row)
    d["ois"] = bool(d["ois"])
    d["is_reference"] = False
    return d


def _to_float(s: str) -> float | None:
    try:
        return float(str(s).replace(",", "."))
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Schema init
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create tables and seed descriptions if the DB is fresh."""
    DATA_DIR.mkdir(exist_ok=True)
    with get_db() as conn:
        _create_tables(conn)
        _seed_descriptions(conn)


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS phones (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL UNIQUE,
            price           TEXT,
            battery         TEXT,
            sensor_size     TEXT,
            aperture        TEXT,
            ois             INTEGER DEFAULT 0,
            max_zoom        TEXT,
            max_video       TEXT,
            storage         TEXT,
            height          REAL,
            width           REAL,
            thickness       REAL,
            link            TEXT,
            recommended_for TEXT
        );
        CREATE TABLE IF NOT EXISTS pro_con (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_id INTEGER NOT NULL REFERENCES phones(id) ON DELETE CASCADE,
            type     TEXT NOT NULL CHECK(type IN ('pro','con')),
            text     TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS column_descriptions (
            column_key  TEXT PRIMARY KEY,
            label       TEXT NOT NULL,
            description TEXT NOT NULL
        );
    """)


def _seed_descriptions(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM column_descriptions").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO column_descriptions(column_key, label, description) VALUES (?,?,?)",
            DEFAULT_DESCRIPTIONS,
        )


# ---------------------------------------------------------------------------
# Phone queries
# ---------------------------------------------------------------------------

def db_list_phones() -> list[dict]:
    """Return all phones with pro/con counts."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT p.*,
                   COUNT(CASE WHEN pc.type='pro' THEN 1 END) AS pro_count,
                   COUNT(CASE WHEN pc.type='con' THEN 1 END) AS con_count
            FROM phones p
            LEFT JOIN pro_con pc ON pc.phone_id = p.id
            GROUP BY p.id
            ORDER BY p.id
        """).fetchall()
    return [_phone_row(r) for r in rows]


def db_get_phone(phone_id: int) -> dict | None:
    """Return a single phone with its pro_con list, or None if not found."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM phones WHERE id=?", (phone_id,)).fetchone()
        if row is None:
            return None
        phone = _phone_row(row)
        pc_rows = conn.execute(
            "SELECT type, text FROM pro_con WHERE phone_id=? ORDER BY type, id",
            (phone_id,),
        ).fetchall()
        phone["pro_con"] = [_row(r) for r in pc_rows]
    return phone


def db_create_phone(data: dict) -> dict:
    """Insert a new phone and its pro/con items. Returns the created phone dict."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO phones
               (name, price, battery, sensor_size, aperture, ois, max_zoom,
                max_video, storage, height, width, thickness, link, recommended_for)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            _phone_params(data, existing=None),
        )
        phone_id = cursor.lastrowid
        _replace_pro_con(conn, phone_id, data.get("pros", []), data.get("cons", []))
        row = conn.execute("SELECT * FROM phones WHERE id=?", (phone_id,)).fetchone()
    return _phone_row(row)


def db_update_phone(phone_id: int, data: dict) -> dict | None:
    """Update an existing phone. Returns updated dict or None if not found."""
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM phones WHERE id=?", (phone_id,)).fetchone()
        if existing is None:
            return None
        conn.execute(
            """UPDATE phones SET
               name=?, price=?, battery=?, sensor_size=?, aperture=?, ois=?,
               max_zoom=?, max_video=?, storage=?, height=?, width=?, thickness=?,
               link=?, recommended_for=?
               WHERE id=?""",
            (*_phone_params(data, existing=existing), phone_id),
        )
        if "pros" in data or "cons" in data:
            _replace_pro_con(conn, phone_id, data.get("pros", []), data.get("cons", []))
        row = conn.execute("SELECT * FROM phones WHERE id=?", (phone_id,)).fetchone()
    return _phone_row(row)


def db_delete_phone(phone_id: int) -> bool:
    """Delete a phone. Returns True if it existed, False otherwise."""
    with get_db() as conn:
        if conn.execute("SELECT 1 FROM phones WHERE id=?", (phone_id,)).fetchone() is None:
            return False
        conn.execute("DELETE FROM phones WHERE id=?", (phone_id,))
    return True


def db_phone_exists(name: str) -> bool:
    with get_db() as conn:
        return conn.execute("SELECT 1 FROM phones WHERE name=?", (name,)).fetchone() is not None


# ---------------------------------------------------------------------------
# Pro/con helpers
# ---------------------------------------------------------------------------

def _replace_pro_con(conn: sqlite3.Connection, phone_id: int, pros: list, cons: list) -> None:
    """Delete all pro/con for phone_id and re-insert from lists."""
    conn.execute("DELETE FROM pro_con WHERE phone_id=?", (phone_id,))
    for text in pros:
        if text.strip():
            conn.execute(
                "INSERT INTO pro_con(phone_id,type,text) VALUES (?,?,?)",
                (phone_id, "pro", text.strip()),
            )
    for text in cons:
        if text.strip():
            conn.execute(
                "INSERT INTO pro_con(phone_id,type,text) VALUES (?,?,?)",
                (phone_id, "con", text.strip()),
            )


def _phone_params(data: dict, existing: sqlite3.Row | None) -> tuple:
    """Build the 14-value tuple for INSERT/UPDATE from request data.
    Falls back to existing row values when a key is missing (for UPDATE).
    """
    def get(key, default=""):
        return data.get(key, _row(existing)[key] if existing else default)

    return (
        (data.get("name") or "").strip() or (existing["name"] if existing else ""),
        get("price"),
        get("battery"),
        get("sensor_size"),
        get("aperture"),
        1 if data.get("ois") else 0,
        get("max_zoom"),
        get("max_video"),
        get("storage"),
        _to_float(str(data["height"])) if data.get("height") else None,
        _to_float(str(data["width"]))  if data.get("width")  else None,
        _to_float(str(data["thickness"])) if data.get("thickness") else None,
        get("link"),
        get("recommended_for"),
    )


# ---------------------------------------------------------------------------
# Column descriptions
# ---------------------------------------------------------------------------

def db_list_descriptions() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM column_descriptions ORDER BY rowid").fetchall()
    return [_row(r) for r in rows]


def db_update_description(column_key: str, description: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE column_descriptions SET description=? WHERE column_key=?",
            (description, column_key),
        )


# ---------------------------------------------------------------------------
# One-time data fix
# ---------------------------------------------------------------------------

def fix_seed_bug() -> None:
    """Remove bad rows created by an early seed typo (text='id')."""
    with get_db() as conn:
        conn.execute("DELETE FROM pro_con WHERE text = 'id'")
