from flask import Flask, render_template, request, redirect
import sqlite3
import psutil
import os
import pandas as pd

app = Flask(__name__)

# ---------------- DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect('db.sqlite3')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_type TEXT,
            description TEXT,
            priority TEXT,
            diagnosis TEXT
        )
    ''')
    conn.close()

# ALWAYS RUN (important for Render)
init_db()

# ---------------- DATABASE CONNECTION ----------------
def get_db_connection():
    conn = sqlite3.connect('db.sqlite3')
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- DIAGNOSTICS FUNCTION ----------------
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

    if not issues:
        return "System running normally"

    return ", ".join(issues)

# ---------------- HOME PAGE ----------------
@app.route('/')
def index():
    conn = get_db_connection()
    tickets = conn.execute('SELECT * FROM tickets').fetchall()
    conn.close()
    return render_template('index.html', tickets=tickets)

# ---------------- CREATE TICKET ----------------
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        issue_type = request.form['issue_type']
        description = request.form['description']
        priority = request.form['priority']

        diagnosis = run_diagnostics()

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO tickets (issue_type, description, priority, diagnosis) VALUES (?, ?, ?, ?)',
            (issue_type, description, priority, diagnosis)
        )
        conn.commit()
        conn.close()

        return redirect('/')

    return render_template('create_ticket.html')

# ---------------- MONITORING PAGE ----------------
@app.route('/monitor')
def monitor():
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent

    return render_template('monitor.html', cpu=cpu, memory=memory, disk=disk)

# ---------------- FIX ISSUES ----------------
@app.route('/fix')
def fix_issue():
    try:
        temp_path = os.getenv('TEMP')

        if temp_path and os.path.exists(temp_path):
            files = os.listdir(temp_path)
            return f"Fix applied: Checked {len(files)} temp files"
        else:
            return "Temp folder not found"

    except Exception as e:
        return f"Error while fixing: {str(e)}"

# ---------------- LOG ANALYSIS ----------------
@app.route('/logs')
def analyze_logs():
    try:
        data = []

        if not os.path.exists('logs.txt'):
            return "No logs file found"

        with open('logs.txt', 'r') as file:
            for line in file:
                parts = line.strip().split(' ', 2)
                if len(parts) == 3:
                    date, level, message = parts
                    data.append([date, level, message])

        df = pd.DataFrame(data, columns=['Date', 'Level', 'Message'])

        summary = df['Level'].value_counts().to_dict()

        return render_template('logs.html', summary=summary)

    except Exception as e:
        return f"Error reading logs: {str(e)}"

# ---------------- RUN APP ----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))