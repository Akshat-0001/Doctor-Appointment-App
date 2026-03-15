import { useEffect, useRef, useState } from 'react';
import { collection, onSnapshot, orderBy, query } from 'firebase/firestore';
import { db } from './firebase';
import './index.css';

const API = 'http://localhost:8030';
// show clean backend host
const API_LABEL = (() => {
  try {
    return new URL(API).host;
  } catch {
    return API;
  }
})();

const post = async (path, body) => {
  // send json post request
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json?.detail || `HTTP ${res.status}`);
  return json;
};

function Auth({ setRole }) {
  // role pick and login
  const [doctorMode, setDoctorMode] = useState(false);
  const [u, setU] = useState('');
  const [p, setP] = useState('');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const login = async () => {
    // verify doctor login creds
    if (!u.trim() || !p || loading) return;
    setErr('');
    setLoading(true);
    try {
      await post('/doctor/login', { username: u.trim(), password: p });
      setRole('doctor');
    } catch {
      setErr('Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="login-card">
        <h1>{doctorMode ? 'Doctor Login' : 'Doctor Appointment Assistant'}</h1>

        {!doctorMode ? (
          <div className="row auth-buttons">
            <button className="btn blue" onClick={() => setRole('patient')}>Patient</button>
            <button className="btn green" onClick={() => setDoctorMode(true)}>Doctor</button>
          </div>
        ) : (
          <>
            <div className="stack">
              <input className="input" placeholder="Doctor username" value={u} onChange={e => setU(e.target.value)} autoFocus />
              <input className="input" type="password" placeholder="Password" value={p} onChange={e => setP(e.target.value)} onKeyDown={e => e.key === 'Enter' && login()} />
              {err && <div className="status">{err}</div>}
            </div>
            <div className="row auth-actions">
              <button className="btn ghost" onClick={() => setDoctorMode(false)}>Back</button>
              <button className="btn green" onClick={login} disabled={loading}>{loading ? 'Signing in...' : 'Login'}</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Patient({ onLogout }) {
  // patient chat booking screen
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hi! Tell me date/time + your name and I'll help book your appointment." },
  ]);
  const historyRef = useRef([]);
  const endRef = useRef(null);

  useEffect(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages, loading]);

  const send = async () => {
    // send message to backend
    const text = input.trim();
    if (!text || loading) return;

    setInput('');
    setMessages(m => [...m, { role: 'user', content: text }]);
    setLoading(true);

    try {
      const r = await post('/chat', { message: text, history: historyRef.current, role: 'patient' });
      const reply = r.reply || 'Done.';
      historyRef.current = [...historyRef.current, { role: 'user', content: text }, { role: 'assistant', content: reply }];
      setMessages(m => [...m, { role: 'assistant', content: reply }]);
    } catch (e) {
      setMessages(m => [...m, { role: 'assistant', content: `⚠️ ${e.message || `Could not reach backend at ${API_LABEL}.`}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <Header title="Doctor Appointment Chat" badge="Patient" badgeClass="blue" onLogout={onLogout} />
      <div className="panel chat">
        {messages.map((m, i) => <div key={i} className={`msg ${m.role}`}>{m.content}</div>)}
        {loading && <div className="thinking">Thinking...</div>}
        <div ref={endRef} />
      </div>
      <div className="composer">
        <input className="input" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} placeholder="Book Dr. Akshat tomorrow 10:00 for John Doe" autoFocus />
        <button className="btn blue" onClick={send} disabled={loading}>Send</button>
      </div>
    </div>
  );
}

function Doctor({ onLogout }) {
  // doctor dashboard and reports
  const today = new Date().toISOString().split('T')[0];
  const [status, setStatus] = useState('');
  const [notes, setNotes] = useState([]);
  const [scope, setScope] = useState('upcoming');
  const [date, setDate] = useState(today);
  const [appointments, setAppointments] = useState({ count: 0, appointments: [] });
  const [loading, setLoading] = useState(false);

  const load = async (nextScope = scope, nextDate = date) => {
    // load filtered appointments data
    setLoading(true);
    try {
      const data = await post('/doctor/appointments', { date: nextScope === 'custom' ? nextDate : null, scope: nextScope });
      setAppointments(data);
    } catch (e) {
      setStatus(`⚠️ ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load('upcoming', today); }, []);

  useEffect(() => {
    if (!db) return setStatus('Firebase not configured - real-time notifications disabled.');
    const q = query(collection(db, 'notifications'), orderBy('timestamp', 'desc'));
    return onSnapshot(q, s => setNotes(s.docs.map(d => ({ id: d.id, ...d.data() }))), e => setStatus(`Firestore error: ${e.message}`));
  }, []);

  const report = async () => {
    // generate today report text
    setStatus('');
    try {
      const r = await post('/doctor/report', { date: today });
      setStatus(r.report || 'Report generated.');
      load(scope, date);
    } catch (e) {
      setStatus(`⚠️ ${e.message}`);
    }
  };

  return (
    <div className="app">
      <Header title="Doctor Dashboard" badge="Doctor" badgeClass="green" onLogout={onLogout} />

      <div className="panel stack">
        <div className="row wrap">
          <button className="btn green" onClick={report}>Generate Today Report</button>
          <button className="btn blue" onClick={() => load(scope, date)} disabled={loading}>{loading ? 'Loading...' : 'Refresh Appointments'}</button>
          <span className="hint">Backend: {API_LABEL}</span>
        </div>

        <div className="box stack">
          <div className="row between">
            <h3>Appointments</h3>
            <span className="pill">{appointments.count} total</span>
          </div>

          <div className="row wrap">
            {['today', 'tomorrow', 'upcoming', 'all'].map(s => (
              <button key={s} className={`btn ${scope === s ? 'blue' : 'ghost'}`} onClick={() => { setScope(s); load(s, date); }}>
                {s[0].toUpperCase() + s.slice(1)}
              </button>
            ))}
            <input type="date" className="input date" value={date} onChange={e => setDate(e.target.value)} />
            <button className={`btn ${scope === 'custom' ? 'blue' : 'ghost'}`} onClick={() => { setScope('custom'); load('custom', date); }}>
              Load Date
            </button>
          </div>

          <div className="table-wrap">
            {appointments.appointments?.length ? (
              <table>
                <thead><tr><th>Date</th><th>Time</th><th>Patient</th><th>Reason</th><th>Status</th></tr></thead>
                <tbody>
                  {appointments.appointments.map(a => (
                    <tr key={a.id}><td>{a.date}</td><td>{a.time}</td><td>{a.patient_name}</td><td>{a.reason || 'General Consultation'}</td><td>{a.status || 'booked'}</td></tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty">No appointments found.</div>
            )}
          </div>
        </div>

        {status && <div className="status">{status}</div>}

        <h3>Live Notifications</h3>
        <div className="stack">
          {notes.length ? notes.map(n => (
            <div key={n.id} className="note">
              <div className="note-title">{n.message}</div>
              <div>{n.body}</div>
            </div>
          )) : <div className="empty">No notifications yet.</div>}
        </div>
      </div>
    </div>
  );
}

function Header({ title, badge, badgeClass, onLogout }) {
  // top header with logout
  return (
    <div className="header">
      <div className="row">
        <strong>{title}</strong>
        <span className={`badge ${badgeClass}`}>{badge}</span>
      </div>
      <button className="btn ghost" onClick={onLogout}>Logout</button>
    </div>
  );
}

export default function App() {
  // route by chosen role
  const [role, setRole] = useState(null);
  if (!role) return <Auth setRole={setRole} />;
  return role === 'patient' ? <Patient onLogout={() => setRole(null)} /> : <Doctor onLogout={() => setRole(null)} />;
}
