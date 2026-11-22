FROM_PREFIX = "from: "


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


def receive(db, source, parts):
    """Add (category, name, qty, tags[, link]) rows to stock, merging into existing parts by name.

    Returns False if this source was already received.
    """
    if db.execute("SELECT 1 FROM intake WHERE name = ?", (source,)).fetchone():
        return False
    for row in parts:
        category, name, qty, tags = row[:4]
        link = row[4] if len(row) > 4 else ""
        existing = db.execute(
            "SELECT * FROM part WHERE name = ? COLLATE NOCASE ORDER BY id LIMIT 1", (name,)
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE part SET qty = ?, tags = ?, notes = ?, link = COALESCE(NULLIF(link, ''), ?), "
                "updated = datetime('now') WHERE id = ?",
                (
                    existing["qty"] + qty,
                    merge_tags(existing["tags"], tags),
                    add_source(existing["notes"], source),
                    link,
                    existing["id"],
                ),
            )
        else:
            db.execute(
                "INSERT INTO part (name, category, qty, tags, notes, link) VALUES (?, ?, ?, ?, ?, ?)",
                (name, category, qty, tags, add_source("", source), link),
            )
    db.execute("INSERT INTO intake (name) VALUES (?)", (source,))
    db.commit()
    return True
