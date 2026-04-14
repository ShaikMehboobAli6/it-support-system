from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import psutil
import os
import shutil
from pathlib import Path

app = Flask(__name__)
DB_PATH = "db.sqlite3"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_type TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL,
            diagnosis TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def run_diagnostics():
    cpu = psutil.cpu_percent(interval=0.2)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent

    issues = []

    if cpu > 80:
        issues.append("High CPU usage")
    if memory > 80:
        issues.append("High Memory usage")
    if disk > 80:
        issues.append("Low Disk Space")

    return ", ".join(issues) if issues else "System normal"


def cleanup_cache_files():
    removed = []

    base = Path.cwd()
    folders = ["cache", "temp", "__pycache__"]

    for folder in folders:
        path = base / folder
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                removed.append(str(path))
            else:
                try:
                    path.unlink()
                    removed.append(str(path))
                except Exception:
                    pass

    patterns = ["*.cache", "*.tmp", "*.temp", "*.pyc"]
    for pattern in patterns:
        for file_path in base.glob(pattern):
            if file_path.is_file():
                try:
                    file_path.unlink()
                    removed.append(str(file_path))
                except Exception:
                    pass

    return removed


def get_top_processes(limit=5):
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            info = proc.info
            processes.append({
                'pid': info['pid'],
                'name': info['name'] or 'Unknown',
                'cpu': round(info['cpu_percent'] or 0, 1),
                'memory': round(info['memory_percent'] or 0, 1)
            })
        except Exception:
            continue

    processes.sort(key=lambda x: (x['cpu'], x['memory']), reverse=True)
    return processes[:limit]


def parse_logs():
    logs = []
    summary = {"INFO": 0, "WARNING": 0, "ERROR": 0}

    if not os.path.exists("logs.txt"):
        return logs, summary

    with open("logs.txt", "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            parts = line.split(" ", 2)
            if len(parts) == 3:
                date, level, message = parts
                level = level.upper()
                logs.append({
                    "date": date,
                    "level": level,
                    "message": message
                })
                if level in summary:
                    summary[level] += 1

    return logs, summary


init_db()


@app.route("/")
def index():
    conn = get_db_connection()
    tickets = conn.execute("SELECT * FROM tickets ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("index.html", tickets=tickets)


@app.route("/create", methods=("GET", "POST"))
def create():
    if request.method == "POST":
        issue_type = request.form["issue_type"]
        description = request.form["description"]
        priority = request.form["priority"]

        diagnosis = run_diagnostics()

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO tickets (issue_type, description, priority, diagnosis, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (issue_type, description, priority, diagnosis, "Open")
        )
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("create_ticket.html")


@app.route("/close/<int:ticket_id>")
def close_ticket(ticket_id):
    conn = get_db_connection()
    conn.execute(
        "UPDATE tickets SET status = 'Closed' WHERE id = ?",
        (ticket_id,)
    )
    conn.commit()
    conn.close()
    return redirect("/")


@app.route("/fix/<int:ticket_id>")
def fix_ticket(ticket_id):
    removed = cleanup_cache_files()
    fix_text = "Cache cleanup done" if removed else "No cache files found"

    conn = get_db_connection()
    ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()

    if ticket:
        updated_diagnosis = f"{ticket['diagnosis']} | Fix applied: {fix_text}"
        conn.execute(
            """
            UPDATE tickets
            SET status = 'Closed', diagnosis = ?
            WHERE id = ?
            """,
            (updated_diagnosis, ticket_id)
        )
        conn.commit()

    conn.close()
    return redirect("/")


@app.route("/cleanup")
def cleanup():
    removed = cleanup_cache_files()
    message = f"Removed {len(removed)} cache/temp files" if removed else "No cache/temp files found"
    return redirect("/")


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()

    conn = get_db_connection()
    tickets = conn.execute(
        """
        SELECT * FROM tickets
        WHERE issue_type LIKE ? OR description LIKE ? OR priority LIKE ? OR status LIKE ?
        ORDER BY id DESC
        """,
        (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%")
    ).fetchall()
    conn.close()

    return render_template("index.html", tickets=tickets, query=query)


@app.route("/monitor")
def monitor():
    return render_template("monitor.html")


@app.route("/api/metrics")
def api_metrics():
    cpu = psutil.cpu_percent(interval=0.2)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    processes = psutil.pids()

    top_processes = get_top_processes(limit=5)

    return jsonify({
        "cpu": cpu,
        "memory": memory,
        "disk": disk,
        "process_count": len(processes),
        "top_processes": top_processes
    })


@app.route("/logs")
def logs():
    logs_list, summary = parse_logs()
    return render_template("logs.html", logs=logs_list, summary=summary)


if __name__ == "__main__":
    app.run(debug=True)