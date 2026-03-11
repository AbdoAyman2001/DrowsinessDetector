import sqlite3


class Repository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create_session(self) -> int:
        cursor = self._conn.execute("INSERT INTO sessions DEFAULT VALUES")
        self._conn.commit()
        return cursor.lastrowid

    def end_session(self, session_id: int):
        self._conn.execute(
            "UPDATE sessions SET ended_at = datetime('now') WHERE id = ?",
            (session_id,),
        )
        self._conn.commit()

    def log_event(self, session_id: int, event_type: str, ear: float, mar: float, duration_frames: int = 0):
        self._conn.execute(
            "INSERT INTO events (session_id, event_type, ear, mar, duration_frames) VALUES (?, ?, ?, ?, ?)",
            (session_id, event_type, ear, mar, duration_frames),
        )
        # Update session counters
        col_map = {
            "drowsy": "total_drowsy_events",
            "microsleep": "total_microsleep_events",
            "yawn": "total_yawn_events",
        }
        col = col_map.get(event_type)
        if col:
            self._conn.execute(
                f"UPDATE sessions SET {col} = {col} + 1 WHERE id = ?",
                (session_id,),
            )
        self._conn.commit()

    def log_snapshot(self, session_id: int, ear: float, mar: float,
                     eye_state: str, yawn_count: int, alarm_level: str, face_detected: bool):
        self._conn.execute(
            """INSERT INTO snapshots
               (session_id, ear, mar, eye_state, yawn_count, alarm_level, face_detected)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, ear, mar, eye_state, yawn_count, alarm_level, int(face_detected)),
        )
        self._conn.commit()

    def get_session(self, session_id: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(row) if row else None

    def get_recent_sessions(self, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_session_events(self, session_id: int) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM events WHERE session_id = ? ORDER BY id", (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_daily_stats(self, days: int = 7) -> list[dict]:
        rows = self._conn.execute(
            """SELECT date(started_at) as date,
                      COUNT(*) as sessions,
                      SUM(total_drowsy_events) as drowsy_events,
                      SUM(total_yawn_events) as yawn_events,
                      SUM(total_microsleep_events) as microsleep_events
               FROM sessions
               WHERE started_at >= datetime('now', ?)
               GROUP BY date(started_at)
               ORDER BY date(started_at) DESC""",
            (f"-{days} days",),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_session_snapshots(self, session_id: int) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM snapshots WHERE session_id = ? ORDER BY id", (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]
