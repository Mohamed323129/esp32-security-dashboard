import streamlit as st
import requests
import time

# --- Configuration ---
# Your specific Firebase API endpoint
FIREBASE_URL = "https://rt-security-system-default-rtdb.europe-west1.firebasedatabase.app/sensors.json"

st.set_page_config(page_title=" Security Dashboard", page_icon="🛡️", layout="wide")

st.title("🛡️ Live Security System Dashboard")
st.markdown("Fetching real-time data from ESP32 via Firebase REST API.")

# --- Fetch Data Function ---
def fetch_sensor_data():
    try:
        response = requests.get(FIREBASE_URL)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"Failed to connect to Firebase: {e}")
        return None

# --- Main Dashboard ---
data = fetch_sensor_data()

if data:
    # Create a nice layout with 4 columns for our 4 sensors
    col1, col2, col3, col4 = st.columns(4)

    # 1. Ultrasonic Distance
    with col1:
        distance = data.get("ultrasonic_cm", -1)
        if distance == -1:
            st.metric("Distance", "Error")
        else:
            st.metric("Distance", f"{distance} cm")

    # 2. Flame Sensor
    with col2:
        flame = data.get("flame_detected", False)
        if flame:
            st.error("🔥 FLAME DETECTED")
        else:
            st.success("Safe")
            st.metric("Flame Sensor", "Clear")

    # 3. Gas Sensor
    with col3:
        gas = data.get("gas_detected", False)
        if gas:
            st.error("💨 GAS LEAK DETECTED")
        else:
            st.success("Safe")
            st.metric("Gas Sensor", "Clear")

    # 4. Magnetic Reed Switch (Door)
    with col4:
        door_open = data.get("door_open", False)
        if door_open:
            st.warning("🚪 DOOR OPEN")
        else:
            st.info("Door Closed")
            st.metric("Security", "Secured")

    # Overall System Status
    st.divider()
    system_alert = data.get("system_alert", False)
    if system_alert:
        st.error("🚨 ALARM ACTIVE - IMMEDIATE ATTENTION REQUIRED 🚨")
    else:
        st.success("✅ System Operating Normally")

else:
    st.warning("Waiting for data from ESP32...")

# --- Auto-Refresh Logic ---
# This forces the Streamlit app to reload every 2 seconds to get fresh data
time.sleep(2)
st.rerun()
