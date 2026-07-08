import json
import sqlite3
from typing import Optional


def _json_loads(val):
    if isinstance(val, str):
        return json.loads(val)
    return val


def _json_dumps(val):
    return json.dumps(val, ensure_ascii=False)


def create_novel(conn, title, genre="", language="zh", premise="",
                 style_guide="", target_audience="", word_count_goal=0):
    cur = conn.execute("""
        INSERT INTO novels (title, genre, language, premise, style_guide, target_audience, word_count_goal)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, genre, language, premise, style_guide, target_audience, word_count_goal))
    conn.commit()
    return cur.lastrowid


def get_novel(conn, novel_id):
    row = conn.execute("SELECT * FROM novels WHERE id=?", (novel_id,)).fetchone()
    if row:
        return dict(row)
    return None


def list_novels(conn):
    rows = conn.execute("SELECT id, title, genre, language, created_at FROM novels ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def update_novel(conn, novel_id, **kwargs):
    allowed = {"title", "genre", "language", "premise", "style_guide",
               "target_audience", "word_count_goal"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = "CURRENT_TIMESTAMP"
    set_clause = ", ".join(f"{k}=?" if k != "updated_at" else f"{k}=CURRENT_TIMESTAMP"
                           for k in updates)
    values = [v for k, v in updates.items() if k != "updated_at"]
    values.append(novel_id)
    conn.execute(f"UPDATE novels SET {set_clause} WHERE id=?", tuple(values))
    conn.commit()


def create_character(conn, novel_id, name, role="", personality="",
                     appearance="", background="", arc="",
                     relationships=None, notes="", first_appearance=0):
    rels = _json_dumps(relationships or {})
    cur = conn.execute("""
        INSERT INTO characters (novel_id, name, role, personality, appearance, background, arc, relationships, notes, first_appearance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (novel_id, name, role, personality, appearance, background, arc, rels, notes, first_appearance))
    conn.commit()
    return cur.lastrowid


def get_character(conn, character_id):
    row = conn.execute("SELECT * FROM characters WHERE id=?", (character_id,)).fetchone()
    if row:
        d = dict(row)
        d["relationships"] = _json_loads(d["relationships"])
        return d
    return None


def get_novel_characters(conn, novel_id):
    rows = conn.execute("SELECT * FROM characters WHERE novel_id=? ORDER BY name", (novel_id,)).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["relationships"] = _json_loads(d["relationships"])
        result.append(d)
    return result


def update_character(conn, character_id, **kwargs):
    allowed = {"name", "role", "personality", "appearance", "background",
               "arc", "relationships", "notes", "first_appearance"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    if "relationships" in updates:
        updates["relationships"] = _json_dumps(updates["relationships"])
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [character_id]
    conn.execute(f"UPDATE characters SET {set_clause} WHERE id=?", tuple(values))
    conn.commit()


def get_characters_by_names(conn, novel_id, names):
    if not names:
        return []
    placeholders = ",".join("?" for _ in names)
    rows = conn.execute(
        f"SELECT * FROM characters WHERE novel_id=? AND name IN ({placeholders})",
        (novel_id, *names)
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["relationships"] = _json_loads(d["relationships"])
        result.append(d)
    return result


def create_chapter(conn, novel_id, chapter_number, title="", outline="",
                   pov="", characters=None, plot_threads=None):
    chars = _json_dumps(characters or [])
    pts = _json_dumps(plot_threads or [])
    cur = conn.execute("""
        INSERT INTO chapters (novel_id, chapter_number, title, outline, pov, characters, plot_threads)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (novel_id, chapter_number, title, outline, pov, chars, pts))
    conn.commit()
    return cur.lastrowid


def get_chapter(conn, chapter_id):
    row = conn.execute("SELECT * FROM chapters WHERE id=?", (chapter_id,)).fetchone()
    if row:
        d = dict(row)
        d["characters"] = _json_loads(d["characters"])
        d["plot_threads"] = _json_loads(d["plot_threads"])
        return d
    return None


def get_chapter_by_number(conn, novel_id, chapter_number):
    row = conn.execute(
        "SELECT * FROM chapters WHERE novel_id=? AND chapter_number=?",
        (novel_id, chapter_number)
    ).fetchone()
    if row:
        d = dict(row)
        d["characters"] = _json_loads(d["characters"])
        d["plot_threads"] = _json_loads(d["plot_threads"])
        return d
    return None


def get_novel_chapters(conn, novel_id):
    rows = conn.execute(
        "SELECT * FROM chapters WHERE novel_id=? ORDER BY chapter_number",
        (novel_id,)
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["characters"] = _json_loads(d["characters"])
        d["plot_threads"] = _json_loads(d["plot_threads"])
        result.append(d)
    return result


def update_chapter(conn, chapter_id, **kwargs):
    allowed = {"title", "outline", "pov", "characters", "plot_threads",
               "status", "word_count"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    if "characters" in updates:
        updates["characters"] = _json_dumps(updates["characters"])
    if "plot_threads" in updates:
        updates["plot_threads"] = _json_dumps(updates["plot_threads"])
    updates["updated_at"] = "CURRENT_TIMESTAMP"
    set_clause = ", ".join(f"{k}=?" if k != "updated_at" else f"{k}=CURRENT_TIMESTAMP"
                           for k in updates)
    values = [v for k, v in updates.items() if k != "updated_at"]
    values.append(chapter_id)
    conn.execute(f"UPDATE chapters SET {set_clause} WHERE id=?", tuple(values))
    conn.commit()


def save_chapter_content(conn, chapter_id, content, version=1, summary="", key_events=None):
    ke = _json_dumps(key_events or [])
    cur = conn.execute("""
        INSERT INTO chapter_contents (chapter_id, version, content, summary, key_events)
        VALUES (?, ?, ?, ?, ?)
    """, (chapter_id, version, content, summary, ke))
    conn.commit()
    return cur.lastrowid


def get_chapter_content(conn, chapter_id, version=None):
    if version:
        row = conn.execute(
            "SELECT * FROM chapter_contents WHERE chapter_id=? AND version=? ORDER BY id DESC LIMIT 1",
            (chapter_id, version)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM chapter_contents WHERE chapter_id=? ORDER BY version DESC LIMIT 1",
            (chapter_id,)
        ).fetchone()
    if row:
        d = dict(row)
        d["key_events"] = _json_loads(d["key_events"])
        return d
    return None


def get_chapter_summaries(conn, novel_id, limit=3):
    rows = conn.execute("""
        SELECT c.chapter_number, c.title, cc.summary, cc.key_events
        FROM chapters c
        JOIN chapter_contents cc ON cc.chapter_id = c.id
        WHERE c.novel_id = ? AND cc.summary != ""
        ORDER BY c.chapter_number DESC
        LIMIT ?
    """, (novel_id, limit)).fetchall()
    return [dict(r) for r in rows]


def create_plot_thread(conn, novel_id, name, description="",
                       status="active", related_chapters=None, notes=""):
    rc = _json_dumps(related_chapters or [])
    cur = conn.execute("""
        INSERT INTO plot_threads (novel_id, name, description, status, related_chapters, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (novel_id, name, description, status, rc, notes))
    conn.commit()
    return cur.lastrowid


def get_novel_plot_threads(conn, novel_id, status=None):
    if status:
        rows = conn.execute(
            "SELECT * FROM plot_threads WHERE novel_id=? AND status=? ORDER BY name",
            (novel_id, status)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM plot_threads WHERE novel_id=? ORDER BY name",
            (novel_id,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["related_chapters"] = _json_loads(d["related_chapters"])
        result.append(d)
    return result


def update_plot_thread(conn, thread_id, **kwargs):
    allowed = {"name", "description", "status", "related_chapters", "notes"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    if "related_chapters" in updates:
        updates["related_chapters"] = _json_dumps(updates["related_chapters"])
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [thread_id]
    conn.execute(f"UPDATE plot_threads SET {set_clause} WHERE id=?", tuple(values))
    conn.commit()


def save_review(conn, chapter_id, version, consistency_issues=None,
                character_voice_issues=None, plot_holes=None,
                suggestions=None, overall_score=0, assessment=""):
    ci = _json_dumps(consistency_issues or [])
    cvi = _json_dumps(character_voice_issues or [])
    ph = _json_dumps(plot_holes or [])
    sg = _json_dumps(suggestions or [])
    cur = conn.execute("""
        INSERT INTO review_notes (chapter_id, version, consistency_issues,
            character_voice_issues, plot_holes, suggestions, overall_score, assessment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (chapter_id, version, ci, cvi, ph, sg, overall_score, assessment))
    conn.commit()
    return cur.lastrowid


def get_review(conn, chapter_id, version=None):
    if version:
        row = conn.execute(
            "SELECT * FROM review_notes WHERE chapter_id=? AND version=? ORDER BY id DESC LIMIT 1",
            (chapter_id, version)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM review_notes WHERE chapter_id=? ORDER BY id DESC LIMIT 1",
            (chapter_id,)
        ).fetchone()
    if row:
        d = dict(row)
        for field in ("consistency_issues", "character_voice_issues",
                       "plot_holes", "suggestions"):
            d[field] = _json_loads(d[field])
        return d
    return None


def create_world_entry(conn, novel_id, category, name, description="", notes=""):
    cur = conn.execute("""
        INSERT INTO world_entries (novel_id, category, name, description, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (novel_id, category, name, description, notes))
    conn.commit()
    return cur.lastrowid


def get_novel_world_entries(conn, novel_id, category=None):
    if category:
        rows = conn.execute(
            "SELECT * FROM world_entries WHERE novel_id=? AND category=? ORDER BY name",
            (novel_id, category)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM world_entries WHERE novel_id=? ORDER BY category, name",
            (novel_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def save_global_memory(conn, novel_id, memory_type, content):
    cur = conn.execute("""
        INSERT INTO global_memory (novel_id, memory_type, content)
        VALUES (?, ?, ?)
    """, (novel_id, memory_type, content))
    conn.commit()
    return cur.lastrowid


def get_global_memory(conn, novel_id, memory_type=None, limit=10):
    if memory_type:
        rows = conn.execute(
            "SELECT * FROM global_memory WHERE novel_id=? AND memory_type=? ORDER BY id DESC LIMIT ?",
            (novel_id, memory_type, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM global_memory WHERE novel_id=? ORDER BY id DESC LIMIT ?",
            (novel_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]
