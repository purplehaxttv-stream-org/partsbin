import os
from collections import defaultdict
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

from .db import close_db, get_db, init_db

STATUSES = ["idea", "building", "done"]


def create_app():
    app = Flask(__name__)
    default_db = Path(__file__).resolve().parent.parent / "data" / "partsbin.db"
    app.config["DATABASE"] = os.environ.get("PARTSBIN_DB", str(default_db))
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    def stock_by_name():
        rows = get_db().execute(
            "SELECT lower(name) AS k, SUM(qty) AS total FROM part GROUP BY lower(name)"
        ).fetchall()
        return {r["k"]: r["total"] for r in rows}

    def reserved_by_name(exclude_project=None):
        sql = (
            "SELECT lower(pp.part_name) AS k, SUM(pp.qty) AS n FROM project_part pp "
            "JOIN project p ON p.id = pp.project_id WHERE p.status = 'building'"
        )
        args = []
        if exclude_project is not None:
            sql += " AND p.id != ?"
            args.append(exclude_project)
        rows = get_db().execute(f"{sql} GROUP BY lower(pp.part_name)", args).fetchall()
        return {r["k"]: r["n"] for r in rows}

    def all_locations():
        return get_db().execute("SELECT * FROM location ORDER BY name").fetchall()

    def all_categories():
        rows = get_db().execute("SELECT DISTINCT category FROM part ORDER BY category").fetchall()
        return [r["category"] for r in rows]

    def all_part_names():
        rows = get_db().execute("SELECT DISTINCT name FROM part ORDER BY name COLLATE NOCASE").fetchall()
        return [r["name"] for r in rows]

    @app.route("/")
    def index():
        q = request.args.get("q", "").strip()
        category = request.args.get("category", "")
        location = request.args.get("location", "")

        sql = (
            "SELECT part.*, location.name AS location_name FROM part "
            "LEFT JOIN location ON location.id = part.location_id WHERE 1=1"
        )
        args = []
        if q:
            like = f"%{q}%"
            sql += " AND (part.name LIKE ? OR part.tags LIKE ? OR part.notes LIKE ? OR part.category LIKE ?)"
            args += [like, like, like, like]
        if category:
            sql += " AND part.category = ?"
            args.append(category)
        if location:
            sql += " AND part.location_id = ?"
            args.append(location)
        sql += " ORDER BY part.category, part.name COLLATE NOCASE, location.name"
        parts = get_db().execute(sql, args).fetchall()

        grouped = defaultdict(list)
        for p in parts:
            grouped[p["category"]].append(p)

        totals = stock_by_name()
        reserved = reserved_by_name()
        total_units = sum(p["qty"] for p in parts)

        return render_template(
            "index.html",
            grouped=grouped,
            totals=totals,
            reserved=reserved,
            q=q,
            category=category,
            location=location,
            categories=all_categories(),
            locations=all_locations(),
            part_count=len(parts),
            total_units=total_units,
        )

    @app.post("/part/<int:part_id>/adjust")
    def adjust(part_id):
        delta = int((request.get_json(silent=True) or {}).get("delta", 0))
        db = get_db()
        row = db.execute("SELECT qty FROM part WHERE id = ?", (part_id,)).fetchone()
        if row is None:
            abort(404)
        new_qty = max(0, row["qty"] + delta)
        db.execute("UPDATE part SET qty = ?, updated = datetime('now') WHERE id = ?", (new_qty, part_id))
        db.commit()
        return jsonify(qty=new_qty)

    def part_from_form():
        f = request.form
        loc = f.get("location_id") or None
        return (
            f["name"].strip(),
            f.get("category", "").strip() or "Misc",
            max(0, int(f.get("qty") or 0)),
            int(loc) if loc else None,
            f.get("tags", "").strip(),
            f.get("notes", "").strip(),
            f.get("link", "").strip(),
        )

    @app.route("/part/new", methods=["GET", "POST"])
    def part_new():
        if request.method == "POST":
            db = get_db()
            db.execute(
                "INSERT INTO part (name, category, qty, location_id, tags, notes, link) VALUES (?,?,?,?,?,?,?)",
                part_from_form(),
            )
            db.commit()
            return redirect(url_for("index"))
        return render_template(
            "part_form.html", part=None, locations=all_locations(),
            categories=all_categories(), names=all_part_names(),
        )

    @app.route("/part/<int:part_id>/edit", methods=["GET", "POST"])
    def part_edit(part_id):
        db = get_db()
        part = db.execute("SELECT * FROM part WHERE id = ?", (part_id,)).fetchone()
        if part is None:
            abort(404)
        if request.method == "POST":
            db.execute(
                "UPDATE part SET name=?, category=?, qty=?, location_id=?, tags=?, notes=?, link=?, "
                "updated=datetime('now') WHERE id=?",
                (*part_from_form(), part_id),
            )
            db.commit()
            return redirect(url_for("index"))
        return render_template(
            "part_form.html", part=part, locations=all_locations(),
            categories=all_categories(), names=all_part_names(),
        )

    @app.post("/part/<int:part_id>/delete")
    def part_delete(part_id):
        db = get_db()
        db.execute("DELETE FROM part WHERE id = ?", (part_id,))
        db.commit()
        return redirect(url_for("index"))

    @app.route("/locations", methods=["GET", "POST"])
    def locations():
        db = get_db()
        if request.method == "POST":
            name = request.form["name"].strip()
            if name:
                db.execute(
                    "INSERT OR IGNORE INTO location (name, notes) VALUES (?, ?)",
                    (name, request.form.get("notes", "").strip()),
                )
                db.commit()
            return redirect(url_for("locations"))
        rows = db.execute(
            "SELECT location.*, COUNT(part.id) AS part_count, COALESCE(SUM(part.qty), 0) AS units "
            "FROM location LEFT JOIN part ON part.location_id = location.id "
            "GROUP BY location.id ORDER BY location.name"
        ).fetchall()
        return render_template("locations.html", locations=rows)

    @app.post("/locations/<int:loc_id>/delete")
    def location_delete(loc_id):
        db = get_db()
        db.execute("DELETE FROM location WHERE id = ?", (loc_id,))
        db.commit()
        return redirect(url_for("locations"))

    def project_status(project_id):
        db = get_db()
        lines = db.execute(
            "SELECT * FROM project_part WHERE project_id = ? ORDER BY part_name COLLATE NOCASE",
            (project_id,),
        ).fetchall()
        totals = stock_by_name()
        reserved = reserved_by_name(exclude_project=project_id)
        result = []
        for line in lines:
            k = line["part_name"].lower()
            have = totals.get(k, 0)
            free = have - reserved.get(k, 0)
            result.append({
                "id": line["id"],
                "name": line["part_name"],
                "need": line["qty"],
                "have": have,
                "free": free,
                "ok": free >= line["qty"],
            })
        return result

    @app.route("/projects", methods=["GET", "POST"])
    def projects():
        db = get_db()
        if request.method == "POST":
            name = request.form["name"].strip()
            if name:
                cur = db.execute(
                    "INSERT OR IGNORE INTO project (name, notes) VALUES (?, ?)",
                    (name, request.form.get("notes", "").strip()),
                )
                db.commit()
                if cur.lastrowid:
                    return redirect(url_for("project", project_id=cur.lastrowid))
            return redirect(url_for("projects"))
        rows = db.execute("SELECT * FROM project ORDER BY status, name").fetchall()
        summary = []
        for p in rows:
            lines = project_status(p["id"])
            missing = sum(1 for line in lines if not line["ok"])
            summary.append({"p": p, "lines": len(lines), "missing": missing})
        return render_template("projects.html", projects=summary)

    @app.route("/project/<int:project_id>", methods=["GET", "POST"])
    def project(project_id):
        db = get_db()
        proj = db.execute("SELECT * FROM project WHERE id = ?", (project_id,)).fetchone()
        if proj is None:
            abort(404)
        if request.method == "POST":
            action = request.form.get("action")
            if action == "add":
                name = request.form["part_name"].strip()
                qty = max(1, int(request.form.get("qty") or 1))
                if name:
                    db.execute(
                        "INSERT INTO project_part (project_id, part_name, qty) VALUES (?, ?, ?)",
                        (project_id, name, qty),
                    )
            elif action == "remove":
                db.execute(
                    "DELETE FROM project_part WHERE id = ? AND project_id = ?",
                    (request.form["line_id"], project_id),
                )
            elif action == "update":
                status = request.form.get("status", "idea")
                if status not in STATUSES:
                    status = "idea"
                db.execute(
                    "UPDATE project SET status = ?, notes = ? WHERE id = ?",
                    (status, request.form.get("notes", "").strip(), project_id),
                )
            db.commit()
            return redirect(url_for("project", project_id=project_id))
        lines = project_status(project_id)
        return render_template(
            "project.html", proj=proj, lines=lines, statuses=STATUSES,
            names=all_part_names(), buildable=all(line["ok"] for line in lines) and bool(lines),
        )

    @app.post("/project/<int:project_id>/delete")
    def project_delete(project_id):
        db = get_db()
        db.execute("DELETE FROM project WHERE id = ?", (project_id,))
        db.commit()
        return redirect(url_for("projects"))

    return app
