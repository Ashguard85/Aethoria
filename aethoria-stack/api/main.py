"""
AETHORIA — Session Backend (Phase B)
FastAPI + SQLite — speichert Kampagnen persistent.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3, json, httpx, os, uuid, time

DB_PATH      = os.getenv('DB_PATH',      '/data/aethoria.db')
OLLAMA_URL   = os.getenv('OLLAMA_URL',   'http://host.docker.internal:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')

app = FastAPI(title='AETHORIA Session API', version='1.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

# ── DB INIT ──
def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id           TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            game_name    TEXT DEFAULT 'Aethoria',
            scenario     TEXT DEFAULT 'Standard',
            round        INTEGER DEFAULT 1,
            total_rounds INTEGER DEFAULT 10,
            mood_idx     INTEGER DEFAULT 1,
            players_json TEXT DEFAULT '[]',
            events_json  TEXT DEFAULT '[]',
            created_at   INTEGER,
            updated_at   INTEGER
        );
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role       TEXT NOT NULL,
            content    TEXT NOT NULL,
            images_b64 TEXT,
            round_num  INTEGER,
            mood       TEXT,
            created_at INTEGER,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_msg_sess ON messages(session_id, id);
        """)

init_db()

# ── MODELS ──
class SessionCreate(BaseModel):
    name: str
    game_name: Optional[str] = 'Aethoria'
    scenario: Optional[str] = 'Standard'
    total_rounds: Optional[int] = 10
    players: Optional[list] = []
    id_hint: Optional[str] = None   # Frontend kann eigene ID vorschlagen

class MessageRequest(BaseModel):
    prompt: str
    image: Optional[str] = None
    round: Optional[int] = 1
    mood: Optional[str] = 'Stabil'
    players: Optional[list] = []

class SessionUpdate(BaseModel):
    round: Optional[int] = None
    mood_idx: Optional[int] = None
    players: Optional[list] = None
    events: Optional[list] = None

# ── HELPERS ──
def get_conversation(sid, db):
    rows = db.execute(
        'SELECT role, content, images_b64 FROM messages WHERE session_id=? ORDER BY id', (sid,)
    ).fetchall()
    msgs = []
    for r in rows:
        m = {'role': r['role'], 'content': r['content']}
        if r['images_b64']:
            m['images'] = json.loads(r['images_b64'])
        msgs.append(m)
    return msgs

def session_dict(row, msgs=None):
    d = dict(row)
    d['players'] = json.loads(d.pop('players_json', '[]'))
    d['events']  = json.loads(d.pop('events_json',  '[]'))
    if msgs is not None:
        d['conversation'] = msgs
    return d

async def call_ollama(messages):
    async with httpx.AsyncClient(timeout=300) as client:
        try:
            r = await client.post(f'{OLLAMA_URL}/api/chat',
                json={'model': OLLAMA_MODEL, 'messages': messages, 'stream': False})
            if r.status_code == 200:
                return r.json()['message']['content']
        except Exception:
            pass
        # Fallback: /api/generate
        sys = next((m['content'] for m in messages if m['role'] == 'system'), '')
        ctx = '\n\n'.join(
            ('### SPIELER:\n' if m['role']=='user' else '### WELT:\n') + m['content']
            for m in messages if m['role'] != 'system'
        )
        body = {'model': OLLAMA_MODEL, 'prompt': sys + '\n\n' + ctx, 'stream': False}
        last = next((m for m in reversed(messages) if m['role']=='user'), None)
        if last and last.get('images'):
            body['images'] = last['images']
        r = await client.post(f'{OLLAMA_URL}/api/generate', json=body)
        r.raise_for_status()
        return r.json()['response']

def build_system_prompt(session, data):
    pl = ', '.join(f"{p.get('name','?')} ({p.get('faction','?')})" for p in (data.players or []))
    return f"""Du bist die WELTMASCHINE des Brettspiels AETHORIA — Das Erbe der zerstörten Welt.
Du spielst als die lebendige Welt selbst: Wirtschaft, Wetter, Natur, Gesellschaft, Unfälle, Aether.

KAMPAGNE: {session.get('game_name','Aethoria')} · Szenario: {session.get('scenario','Standard')}
SPIELER: {pl}

SPIELWELT: Aethoria wurde vor 300 Jahren durch einen Magikerunfall zerstört. Aetherwunden durchziehen das Land.

WICHTIG: Du erinnerst dich an ALLE vorherigen Runden dieser Kampagne. Baue narrativ auf dem Vergangenen auf. Reagiere auf Trends, Eskalationen und Fehler der Spieler. Die Welt hat ein Gedächtnis.

FORMAT: 3-4 Sätze Weltereignis (Deutsch), dann 2-4 Effekte als "EFFEKT: [Beschreibung]"."""

def build_user_prompt(data):
    pts = ', '.join(f"{p.get('name','?')}: {p.get('pts',0)} SP" for p in (data.players or []))
    parts = [f"RUNDE {data.round} · Weltlage: {data.mood}"]
    if pts: parts.append(f"Stand: {pts}")
    if data.image: parts.append("[Spielfeld-Foto übermittelt]")
    parts.append(f"\nBERICHT: {data.prompt}")
    return '\n'.join(parts)

# ── ROUTES ──
@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'aethoria-api', 'version': '1.0'}

@app.post('/session', status_code=201)
def create_session(data: SessionCreate):
    # Verwende id_hint vom Frontend wenn vorhanden (Session-ID-Sync)
    sid = data.id_hint if (data.id_hint and data.id_hint.startswith('sess-')) \
          else 'sess-' + uuid.uuid4().hex[:12]
    now = int(time.time() * 1000)
    with get_db() as db:
        db.execute(
            'INSERT INTO sessions(id,name,game_name,scenario,total_rounds,players_json,events_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
            (sid, data.name, data.game_name, data.scenario, data.total_rounds, json.dumps(data.players), '[]', now, now)
        )
    return {'id': sid, 'name': data.name, 'created_at': now}

@app.get('/session')
def list_sessions():
    with get_db() as db:
        rows = db.execute('SELECT * FROM sessions ORDER BY updated_at DESC').fetchall()
    return [session_dict(r) for r in rows]

@app.get('/session/{sid}')
def get_session(sid: str):
    with get_db() as db:
        row = db.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone()
        if not row: raise HTTPException(404, 'Session nicht gefunden')
        msgs = get_conversation(sid, db)
    return session_dict(row, msgs)

@app.patch('/session/{sid}')
def update_session(sid: str, data: SessionUpdate):
    updates, vals = [], []
    if data.round    is not None: updates.append('round=?');         vals.append(data.round)
    if data.mood_idx is not None: updates.append('mood_idx=?');      vals.append(data.mood_idx)
    if data.players  is not None: updates.append('players_json=?');  vals.append(json.dumps(data.players))
    if data.events   is not None: updates.append('events_json=?');   vals.append(json.dumps(data.events))
    if not updates: return {'ok': True}
    updates.append('updated_at=?')
    vals += [int(time.time()*1000), sid]
    with get_db() as db:
        db.execute(f'UPDATE sessions SET {",".join(updates)} WHERE id=?', vals)
    return {'ok': True}

@app.post('/session/{sid}/message')
async def send_message(sid: str, data: MessageRequest):
    with get_db() as db:
        row = db.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone()
        if not row: raise HTTPException(404, 'Session nicht gefunden')
        conversation = get_conversation(sid, db)

    now = int(time.time() * 1000)
    # System-Prompt beim ersten Aufruf einfügen
    if not any(m['role'] == 'system' for m in conversation):
        sys_content = build_system_prompt(dict(row), data)
        with get_db() as db:
            db.execute(
                'INSERT INTO messages(session_id,role,content,round_num,mood,created_at) VALUES(?,?,?,?,?,?)',
                (sid, 'system', sys_content, data.round, data.mood, now)
            )
        conversation.insert(0, {'role': 'system', 'content': sys_content})

    # User-Nachricht speichern
    user_content = build_user_prompt(data)
    images_json = json.dumps([data.image]) if data.image else None
    with get_db() as db:
        db.execute(
            'INSERT INTO messages(session_id,role,content,images_b64,round_num,mood,created_at) VALUES(?,?,?,?,?,?,?)',
            (sid, 'user', user_content, images_json, data.round, data.mood, now+1)
        )

    # Ollama aufrufen
    user_msg = {'role': 'user', 'content': user_content}
    if data.image: user_msg['images'] = [data.image]
    try:
        response = await call_ollama(conversation + [user_msg])
    except Exception as e:
        raise HTTPException(502, f'Ollama Fehler: {e}')

    # Antwort speichern
    with get_db() as db:
        db.execute(
            'INSERT INTO messages(session_id,role,content,round_num,created_at) VALUES(?,?,?,?,?)',
            (sid, 'assistant', response, data.round, now+2)
        )
        db.execute('UPDATE sessions SET round=?,updated_at=? WHERE id=?', (data.round, now+3, sid))
        updated_conv = get_conversation(sid, db)

    return {'response': response, 'conversation': updated_conv, 'session_id': sid}

@app.delete('/session/{sid}')
def delete_session(sid: str):
    with get_db() as db:
        db.execute('DELETE FROM sessions WHERE id=?', (sid,))
    return {'ok': True}

@app.get('/session/{sid}/export')
def export_session(sid: str):
    with get_db() as db:
        row = db.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone()
        if not row: raise HTTPException(404, 'Session nicht gefunden')
        msgs = get_conversation(sid, db)
    return session_dict(row, msgs)
