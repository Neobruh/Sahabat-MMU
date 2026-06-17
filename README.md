# Sahabat-MMU

A social platform with real-time messaging, built with Flask and Socket.IO.

---

## Prerequisites

- Python 3.10 or higher → https://www.python.org/downloads/
- Git → https://git-scm.com/downloads

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/Sahabat-MMU.git
cd Sahabat-MMU
```

---

### 2. Create a virtual environment

```bash
python -m venv venv
```

---

### 3. Activate the virtual environment

**Windows — Command Prompt (recommended):**
```cmd
venv\Scripts\activate.bat
```

**Windows — PowerShell** (if you get a security error, run this once as Administrator first):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then:
```powershell
venv\Scripts\activate
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

You'll know it's active when you see `(venv)` at the start of your terminal prompt.

---

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

---

### 5. Run the app

```bash
python app.py
```

Then check the console for the link, example: `` * Running on http://127.0.0.1:5000 ``

---

## Troubleshooting

**`venv\Scripts\activate` is blocked on PowerShell**
Use `cmd.exe` instead and run `venv\Scripts\activate.bat`, or see step 3 above for the PowerShell fix.

**`ModuleNotFoundError`**
Make sure your virtual environment is activated (you should see `(venv)` in your prompt) before running `pip install` or `python app.py`.

**Port 5000 already in use**
Another app is using port 5000. Either stop that app, or run on a different port:
```bash
python app.py --port 5001
```

**WebSocket not connecting**
Make sure `eventlet` installed correctly. You can verify with:
```bash
pip show eventlet
```

---

## Tech stack

- [Flask](https://flask.palletsprojects.com/) — web framework
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/) — database ORM
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/) — real-time messaging
- [Werkzeug](https://werkzeug.palletsprojects.com/) — password hashing and file uploads
- [Socket.IO](https://socket.io/) — WebSocket client (browser)