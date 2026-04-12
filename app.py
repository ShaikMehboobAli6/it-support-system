from flask import Flask, render_template, request, redirect
import sqlite3
import psutil

app = Flask(__name__)

# ---------------- DB CONNECTION ----------------
def get_db_connection():
    conn = sqlite3.connect('db.sqlite3')
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- INIT DB ----------------
def init_db():
    conn = sqlite3.connect('db.sqlite3')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_type TEXT,
            description TEXT,
            priority TEXT,
            diagnosis TEXT,
            status TEXT DEFAULT 'Open'
        )
    ''')
    conn.close()

init_db()

# ---------------- HOME ----------------
@app.route('/')
def index():
    conn = get_db_connection()
    tickets = conn.execute('SELECT * FROM tickets').fetchall()
    conn.close()
    return render_template('index.html', tickets=tickets)

# ---------------- CREATE ----------------
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        issue_type = request.form['issue_type']
        description = request.form['description']
        priority = request.form['priority']

        diagnosis = run_diagnostics()
        status = "Open"

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO tickets (issue_type, description, priority, diagnosis, status) VALUES (?, ?, ?, ?, ?)',
            (issue_type, description, priority, diagnosis, status)
        )
        conn.commit()
        conn.close()

        return redirect('/')

    return render_template('create_ticket.html')

# ---------------- CLOSE TICKET ----------------
@app.route('/close/<int:id>')
def close_ticket(id):
    conn = get_db_connection()
    conn.execute('UPDATE tickets SET status = "Closed" WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/')

# ---------------- SEARCH ----------------
@app.route('/search')
def search():
    query = request.args.get('q')

    conn = get_db_connection()
    tickets = conn.execute(
        "SELECT * FROM tickets WHERE issue_type LIKE ? OR description LIKE ?",
        ('%' + query + '%', '%' + query + '%')
    ).fetchall()
    conn.close()

    return render_template('index.html', tickets=tickets)

# ---------------- DIAGNOSTICS ----------------
def run_diagnostics():
    cpu = psutil.cpu_percent()
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

# ---------------- MONITOR ----------------
@app.route('/monitor')
def monitor():
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent

    return render_template('monitor.html', cpu=cpu, memory=memory, disk=disk)

# ---------------- LOGS ----------------
@app.route('/logs')
def logs():
    summary = {
        "INFO": 10,
        "WARNING": 2,
        "ERROR": 1
    }
    return render_template('logs.html', summary=summary)

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)