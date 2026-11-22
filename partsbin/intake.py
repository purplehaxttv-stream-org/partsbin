FROM_PREFIX = "from: "
LEVELS = ["out", "low", "plenty"]


def add_source(notes, source):
    lines = notes.splitlines() if notes else []
    for i, line in enumerate(lines):
        if line.startswith(FROM_PREFIX):
            sources = [s.strip() for s in line[len(FROM_PREFIX):].split(",") if s.strip()]
            if source not in sources:
                sources.append(source)
            lines[i] = f"{FROM_PREFIX}{', '.join(sources)}"
            return "\n".join(lines)
    return "\n".join([*lines, f"{FROM_PREFIX}{source}"])


def merge_tags(a, b):
    tags = []
    for t in f"{a},{b}".split(","):
        t = t.strip()
        if t and t not in tags:
            tags.append(t)
    return ", ".join(tags)


def normalize(row):
    """Accept a 4..7 tuple and return a dict with defaults filled in.

    (category, name, qty, tags[, link[, track[, level]]])
    If the qty field is a level word (out/low/plenty), it is treated as a level part.
    """
    category, name, qty = row[0], row[1], row[2]
    tags = row[3] if len(row) > 3 else ""
    link = row[4] if len(row) > 4 else ""
    track = row[5] if len(row) > 5 else "count"
    level = row[6] if len(row) > 6 else "plenty"
    if isinstance(qty, str) and qty.strip().lower() in LEVELS:
        track = "level"
        level = qty.strip().lower()
        qty = 0
    return {
        "category": category, "name": name, "qty": int(qty or 0),
        "tags": tags, "link": link, "track": track, "level": level,
    }


def receive(db, source, parts):
    """Merge rows into stock by name. Returns False if this source was already received.

    Count parts add their qty; level parts set the stock level (no qty math).
    """
    if db.execute("SELECT 1 FROM intake WHERE name = ?", (source,)).fetchone():
        return False
    for raw in parts:
        p = normalize(raw)
        existing = db.execute(
            "SELECT * FROM part WHERE name = ? COLLATE NOCASE ORDER BY id LIMIT 1", (p["name"],)
        ).fetchone()
        if existing:
            if p["track"] == "level":
                db.execute(
                    "UPDATE part SET track='level', level=?, tags=?, notes=?, updated=datetime('now') WHERE id=?",
                    (p["level"], merge_tags(existing["tags"], p["tags"]),
                     add_source(existing["notes"], source), existing["id"]),
                )
            else:
                db.execute(
                    "UPDATE part SET qty=?, tags=?, notes=?, link=COALESCE(NULLIF(link,''), ?), "
                    "updated=datetime('now') WHERE id=?",
                    (existing["qty"] + p["qty"], merge_tags(existing["tags"], p["tags"]),
                     add_source(existing["notes"], source), p["link"], existing["id"]),
                )
        else:
            db.execute(
                "INSERT INTO part (name, category, qty, track, level, tags, notes, link) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (p["name"], p["category"], p["qty"], p["track"], p["level"],
                 p["tags"], add_source("", source), p["link"]),
            )
    db.execute("INSERT INTO intake (name) VALUES (?)", (source,))
    db.commit()
    return True


def parse_bulk(text, default_category="Misc"):
    """Parse pasted lines into part rows for receive().

    One part per line, fields separated by ';':
        name ; category ; qty-or-level ; tags
    Only name is required. qty-or-level defaults to 1; a word out/low/plenty makes it a level part.
    Blank lines and lines starting with # are ignored.
    """
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = [f.strip() for f in line.split(";")]
        name = fields[0]
        if not name:
            continue
        category = fields[1] if len(fields) > 1 and fields[1] else default_category
        amount = fields[2] if len(fields) > 2 and fields[2] else "1"
        tags = fields[3] if len(fields) > 3 else ""
        if amount.lower() in LEVELS:
            rows.append((category, name, amount.lower(), tags))
        else:
            try:
                qty = int(amount)
            except ValueError:
                qty = 1
            rows.append((category, name, qty, tags))
    return rows
