# ============================================================
#  ESP32 Home Security Dashboard
#  Course: EED420 – Real-time Embedded Systems
#  Stack : Streamlit + Firebase Realtime Database
# ============================================================

import streamlit as st
import requests
import time
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
FIREBASE_URL = "https://rt-security-system-default-rtdb.europe-west1.firebasedatabase.app/sensors.json"
REFRESH_INTERVAL = 2   # seconds between auto-refresh


# ─────────────────────────────────────────────
#  PAGE SETUP
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="ESP32 Security Dashboard",
    page_icon="🔒",
    layout="wide",
)


# ─────────────────────────────────────────────
#  CUSTOM CSS  (dark IoT theme)
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── Global background & font ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0a1628;
    color: #e2e8f0;
    font-family: 'Segoe UI', sans-serif;
}

/* Hide Streamlit default toolbar */
[data-testid="stToolbar"] { display: none; }
header { visibility: hidden; }
footer { visibility: hidden; }

/* ── Main content padding ── */
.block-container { padding: 1.5rem 2rem 2rem 2rem; }

/* ── Dashboard header ── */
.dash-header {
    text-align: center;
    padding: 2rem 1rem 0.5rem 1rem;
}
.dash-header h1 {
    font-size: 2.4rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.5px;
    margin-bottom: 0.2rem;
}
.dash-header p {
    font-size: 1rem;
    color: #64748b;
    margin-top: 0;
}
.dash-header .dot {
    display: inline-block;
    width: 10px; height: 10px;
    border-radius: 50%;
    background: #22c55e;
    margin-right: 6px;
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.3; }
}

/* ── Generic card ── */
.card {
    background: #0f2044;
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    border: 1px solid #1e3a6e;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    transition: transform 0.15s;
}
.card:hover { transform: translateY(-2px); }

/* ── Sensor card internals ── */
.card-icon   { font-size: 2.2rem; margin-bottom: 0.4rem; }
.card-label  { font-size: 0.78rem; color: #64748b; text-transform: uppercase;
               letter-spacing: 1px; margin-bottom: 0.2rem; }
.card-value  { font-size: 1.55rem; font-weight: 700; margin-bottom: 0.2rem; }
.card-sub    { font-size: 0.82rem; color: #94a3b8; }

/* ── Status colours ── */
.safe    { color: #22c55e; }
.danger  { color: #ef4444; }
.warning { color: #f59e0b; }
.info    { color: #38bdf8; }
.muted   { color: #64748b; }

/* ── Overall status banner ── */
.status-banner {
    border-radius: 14px;
    padding: 1.2rem 1.8rem;
    margin-bottom: 1.4rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    border: 1px solid;
}
.status-banner.normal {
    background: #052e16;
    border-color: #16a34a;
}
.status-banner.alarm {
    background: #450a0a;
    border-color: #dc2626;
    animation: flash 1s infinite;
}
@keyframes flash {
    0%, 100% { border-color: #dc2626; }
    50%       { border-color: #7f1d1d; }
}
.status-icon  { font-size: 2.5rem; }
.status-text h2 { margin: 0; font-size: 1.5rem; font-weight: 800; }
.status-text p  { margin: 0; font-size: 0.85rem; color: #94a3b8; }

/* ── Section separator label ── */
.section-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #334155;
    margin: 1.2rem 0 0.6rem 0;
    border-bottom: 1px solid #1e3a6e;
    padding-bottom: 0.3rem;
}

/* ── Timestamp footer ── */
.refresh-bar {
    text-align: center;
    font-size: 0.78rem;
    color: #334155;
    margin-top: 1rem;
    padding: 0.5rem;
    border-top: 1px solid #1e3a6e;
}

/* ── Expander override ── */
[data-testid="stExpander"] {
    background: #0f2044;
    border: 1px solid #1e3a6e;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  HELPER: render one sensor card
# ─────────────────────────────────────────────
def sensor_card(icon, label, value, sub_text, status):
    """
    Renders a styled sensor card.
    status can be: 'safe', 'danger', 'warning', 'info', or 'muted'
    """
    st.markdown(f"""
    <div class="card">
        <div class="card-icon">{icon}</div>
        <div class="card-label">{label}</div>
        <div class="card-value {status}">{value}</div>
        <div class="card-sub">{sub_text}</div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  HELPER: render alarm output card
# ─────────────────────────────────────────────
def alarm_card(icon, label, is_on):
    """Renders buzzer / LED status card."""
    value  = "ON"  if is_on else "OFF"
    status = "danger" if is_on else "safe"
    sub    = "⚠️ Active alarm output" if is_on else "Standby — no threat"
    sensor_card(icon, label, value, sub, status)


# ─────────────────────────────────────────────
#  DATA FETCHING  (from Firebase)
# ─────────────────────────────────────────────
def fetch_data():
    """
    Calls the Firebase REST API and returns a dict of sensor values.
    Returns None if the request fails.
    """
    try:
        response = requests.get(FIREBASE_URL, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────
#  DASHBOARD LAYOUT
# ─────────────────────────────────────────────

# ── Header ──────────────────────────────────
st.markdown("""
<div class="dash-header">
    <h1>🔒 ESP32 Home Security Dashboard</h1>
    <p><span class="dot"></span>Real-time monitoring via Firebase Realtime Database</p>
</div>
""", unsafe_allow_html=True)

# ── Fetch data from Firebase ─────────────────
data = fetch_data()

# ── No data: show warning and stop ──────────
if data is None:
    st.markdown("""
    <div class="card" style="text-align:center; padding: 2.5rem;">
        <div style="font-size:3rem;">📡</div>
        <div class="card-value warning" style="margin-top:0.5rem;">Waiting for ESP32 data...</div>
        <div class="card-sub">Could not reach Firebase. Check your connection or ESP32.</div>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(REFRESH_INTERVAL)
    st.rerun()

# ── Extract sensor values from Firebase dict ─
# Use .get() with safe defaults so the app
# never crashes on a missing key
ultrasonic_cm   = data.get("ultrasonic_cm",   -1)
flame_detected  = data.get("flame_detected",  False)
gas_detected    = data.get("gas_detected",    False)
door_open       = data.get("door_open",       False)
system_alert    = data.get("system_alert",    False)
buzzer_on       = data.get("buzzer_on",       False)
led_on          = data.get("led_on",          False)

# ── Ultrasonic sensor logic ──────────────────
if ultrasonic_cm == -1:
    ultra_value  = "Sensor Error"
    ultra_sub    = "Check wiring / TRIG-ECHO pins"
    ultra_status = "warning"
elif ultrasonic_cm < 30:
    ultra_value  = f"{ultrasonic_cm} cm"
    ultra_sub    = "⚠️ Object detected within 30 cm"
    ultra_status = "danger"
else:
    ultra_value  = f"{ultrasonic_cm} cm"
    ultra_sub    = "No object in range"
    ultra_status = "safe"

# ── Flame sensor logic ───────────────────────
if flame_detected:
    flame_value  = "Flame Detected 🔥"
    flame_sub    = "Fire hazard — alarm triggered"
    flame_status = "danger"
else:
    flame_value  = "Clear"
    flame_sub    = "No flame detected"
    flame_status = "safe"

# ── Gas sensor logic ─────────────────────────
if gas_detected:
    gas_value  = "Gas Detected 💨"
    gas_sub    = "Harmful gas / smoke above threshold"
    gas_status = "danger"
else:
    gas_value  = "Clear"
    gas_sub    = "Air quality normal"
    gas_status = "safe"

# ── Door sensor logic ────────────────────────
if door_open:
    door_value  = "Door Open 🚪"
    door_sub    = "Intrusion or entry detected"
    door_status = "warning"
else:
    door_value  = "Door Closed"
    door_sub    = "Secured"
    door_status = "safe"

# ── Overall system status ────────────────────
if system_alert:
    banner_class = "alarm"
    banner_icon  = "🚨"
    banner_title = "ALARM ACTIVE"
    banner_sub   = "One or more sensors have detected a threat"
else:
    banner_class = "normal"
    banner_icon  = "✅"
    banner_title = "SYSTEM NORMAL"
    banner_sub   = "All sensors are within safe parameters"

# ── Render overall status banner ─────────────
st.markdown(f"""
<div class="status-banner {banner_class}">
    <div class="status-icon">{banner_icon}</div>
    <div class="status-text">
        <h2 class="{'danger' if system_alert else 'safe'}">{banner_title}</h2>
        <p>{banner_sub}</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Section label: Sensors ───────────────────
st.markdown('<div class="section-label">📡 Sensor Readings</div>', unsafe_allow_html=True)

# ── Four sensor cards in a 2 × 2 grid ───────
col1, col2 = st.columns(2)

with col1:
    sensor_card("📏", "HC-SR04 Ultrasonic Distance",
                ultra_value, ultra_sub, ultra_status)

    sensor_card("🌫️", "MQ135 Gas Sensor",
                gas_value, gas_sub, gas_status)

with col2:
    sensor_card("🔥", "KY-026 Flame Sensor",
                flame_value, flame_sub, flame_status)

    sensor_card("🚪", "Magnetic Reed Door Sensor",
                door_value, door_sub, door_status)

# ── Section label: Alarm Outputs ─────────────
st.markdown('<div class="section-label">🔔 Alarm Outputs</div>', unsafe_allow_html=True)

col3, col4 = st.columns(2)

with col3:
    alarm_card("🔔", "Buzzer Status", buzzer_on)

with col4:
    alarm_card("💡", "LED Indicator", led_on)

# ── Raw Firebase data (inside expander) ──────
with st.expander("🗄️  Raw Firebase Data"):
    st.json(data)

# ── Last refresh timestamp ───────────────────
now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
st.markdown(f'<div class="refresh-bar">🕐 Last refreshed: {now} &nbsp;|&nbsp; Auto-refresh every {REFRESH_INTERVAL}s</div>',
            unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  AUTO-REFRESH  (simple sleep + rerun)
# ─────────────────────────────────────────────
time.sleep(REFRESH_INTERVAL)
st.rerun()
