"""Durable writing lanes with optimistic revisions and explicit source references."""

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
import uuid

LANES = ("left", "center", "right")
FORMATS = ("dialogue", "prose", "markdown", "notes")
REFERENCE = re.compile(r"\{\{(left|right)(?::([1-9][0-9]*))?\}\}")
MAX_RENDERED_CHARACTERS = 262144


class Conflict(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def empty_section(title):
    return {
        "id": uuid.uuid4().hex,
        "title": title,
        "lanes": {
            lane: {
                "speaker": {"left": "Mira", "center": "Narrator", "right": "Ren"}[lane],
                "format": "prose" if lane == "center" else "dialogue",
                "text": "",
                "revision": 0,
            }
            for lane in LANES
        },
    }


def render(section):
    lanes = section["lanes"]
    rendered_size = len(lanes["center"]["text"])

    def insert(match):
        nonlocal rendered_size
        name, number = match.groups()
        lane = lanes[name]
        lines = lane["text"].splitlines()
        if number:
            index = int(number) - 1
            if index >= len(lines):
                raise ValueError(f"{name} has no line {number}")
            lines = [lines[index]]
        if lane["format"] == "dialogue":
            result = "\n".join(f"{lane['speaker']}: {line}" if line else "" for line in lines)
        elif lane["format"] == "notes":
            result = "\n".join("- " + line if line else "" for line in lines)
        else:
            result = "\n".join(lines)
        rendered_size += len(result) - len(match[0])
        if rendered_size > MAX_RENDERED_CHARACTERS:
            raise ValueError("Combined section is too long. Split it into smaller sections.")
        return result

    template = lanes["center"]["text"]
    # Invalid references fail before any replacement; inserted source text is never reparsed.
    if "{{" in REFERENCE.sub("", template):
        raise ValueError("Use {{left}}, {{right}} or a positive line number such as {{left:1}}.")
    text = REFERENCE.sub(insert, template)
    return {
        "text": text,
        "sha256": digest(text),
        "sources": {name: {"revision": lane["revision"], "sha256": digest(lane)} for name, lane in lanes.items()},
    }


class BoardStore:
    def __init__(self, file):
        self.file = Path(file)
        self.file.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS boards (id TEXT PRIMARY KEY, body TEXT NOT NULL, updated REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS lane_history (
                    board TEXT, section TEXT, lane TEXT, revision INTEGER, body TEXT,
                    PRIMARY KEY (board,section,lane,revision));
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.file, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def list(self):
        with self.connect() as db:
            return [
                {"id": row[0], "title": json.loads(row[1])["title"], "updated": row[2]}
                for row in db.execute("SELECT id,body,updated FROM boards ORDER BY updated DESC")
            ]

    def create(self, title):
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
            raise ValueError("Title must be 1–120 characters")
        board = {
            "id": uuid.uuid4().hex,
            "title": title.strip(),
            "revision": 0,
            "sections": [empty_section("Opening scene")],
        }
        with self.connect() as db:
            db.execute("INSERT INTO boards VALUES (?,?,?)", (board["id"], json.dumps(board), time.time()))
        return board

    @staticmethod
    def read(db, board_id):
        row = db.execute("SELECT body FROM boards WHERE id=?", (board_id,)).fetchone()
        if row is None:
            raise KeyError("Board not found")
        return json.loads(row[0])

    def get(self, board_id):
        with self.connect() as db:
            return self.read(db, board_id)

    @staticmethod
    def section(board, section_id):
        section = next((s for s in board["sections"] if s["id"] == section_id), None)
        if section is None:
            raise KeyError("Section not found")
        return section

    @staticmethod
    def check_context(section, expected):
        if expected is not None:
            if set(expected) != set(LANES) or any(type(v) is not int for v in expected.values()):
                raise ValueError("Expected revisions must name all three lanes")
            if any(section["lanes"][k]["revision"] != v for k, v in expected.items()):
                raise Conflict("Source lanes changed. Review or generate a new proposal.")

    @staticmethod
    def write(db, board):
        board["revision"] += 1
        db.execute("UPDATE boards SET body=?,updated=? WHERE id=?", (json.dumps(board), time.time(), board["id"]))

    def add_section(self, board_id, title):
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
            raise ValueError("Section title must be 1–120 characters")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            board = self.read(db, board_id)
            if len(board["sections"]) >= 100:
                raise ValueError("This board has reached 100 sections")
            board["sections"].append(empty_section(title.strip()))
            self.write(db, board)
            return board

    def outline(self, board_id, expected_revision, title, sections):
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
            raise ValueError("Title must be 1–120 characters")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            board = self.read(db, board_id)
            if type(expected_revision) is not int or board["revision"] != expected_revision:
                raise Conflict("The document changed. Reload its outline before reorganizing it.")
            current = {s["id"]: s for s in board["sections"]}
            ids = [s["id"] for s in sections]
            if len(ids) != len(set(ids)) or set(ids) != set(current):
                raise ValueError("Outline must contain every section exactly once")
            for item in sections:
                if not isinstance(item["title"], str) or not 1 <= len(item["title"].strip()) <= 120:
                    raise ValueError("Section title must be 1–120 characters")
            board["title"] = title.strip()
            board["sections"] = [dict(current[s["id"]], title=s["title"].strip()) for s in sections]
            self.write(db, board)
            return board

    def update(self, board_id, section_id, lane, expected_revision, text, speaker, format, expected_context=None):
        if lane not in LANES or format not in FORMATS:
            raise ValueError("Unknown lane or format")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("Revision must be a nonnegative integer")
        if not isinstance(text, str) or len(text) > 65536 or "\0" in text:
            raise ValueError("Lane text must be at most 65536 characters, without NUL")
        if not isinstance(speaker, str) or not 1 <= len(speaker.strip()) <= 80:
            raise ValueError("Speaker must be 1–80 characters")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            board = self.read(db, board_id)
            section = self.section(board, section_id)
            self.check_context(section, expected_context)
            previous = section["lanes"][lane]
            if previous["revision"] != expected_revision:
                raise Conflict("This lane changed. Reload before applying your edit.")
            db.execute(
                "INSERT OR IGNORE INTO lane_history VALUES (?,?,?,?,?)",
                (board_id, section_id, lane, previous["revision"], json.dumps(previous)),
            )
            section["lanes"][lane] = {
                "speaker": speaker.strip(),
                "format": format,
                "text": text,
                "revision": expected_revision + 1,
            }
            db.execute(
                "INSERT INTO lane_history VALUES (?,?,?,?,?)",
                (board_id, section_id, lane, expected_revision + 1, json.dumps(section["lanes"][lane])),
            )
            self.write(db, board)
            return board

    def history(self, board_id, section_id, lane):
        if lane not in LANES:
            raise ValueError("Unknown lane")
        with self.connect() as db:
            self.section(self.read(db, board_id), section_id)
            return [
                json.loads(r[0])
                for r in db.execute(
                    "SELECT body FROM lane_history WHERE board=? AND section=? AND lane=? ORDER BY revision DESC LIMIT 50",
                    (board_id, section_id, lane),
                )
            ]
