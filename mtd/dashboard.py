import os
import time

import pyotp
import streamlit as st

st.set_page_config(page_title="MTD Defense Dashboard", layout="wide", page_icon="🛡️")
st.title("🛡️ Moving Target Defence — Live Threat Dashboard")

SHARED_SECRET = "JBSWY3DPEHPK3PXP"
EPOCH = 30
TOTP = pyotp.TOTP(SHARED_SECRET)
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "shared_logs", "attack.log")

placeholder = st.empty()

while True:
    port = 8000 + (int(TOTP.now()) % 50)
    remaining = EPOCH - (int(time.time()) % EPOCH)
    rows = []
    try:
        with open(LOG_PATH) as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    rows.append({"Trapped Attacker IP": parts[0],
                                 "Port They Attacked": parts[1],
                                 "Timestamp": parts[2] if len(parts) > 2 else ""})
    except FileNotFoundError:
        pass

    with placeholder.container():
        c1, c2, c3 = st.columns(3)
        c1.metric("Current Secure Port", port)
        c2.metric("Next Port Shift In", f"{remaining}s")
        c3.metric("Defense Status", "MOVING")
        st.subheader("🚫 Trapped Attacker IPs")
        if rows:
            st.dataframe(rows[::-1], use_container_width=True)
            st.metric("Total Unique Attackers", len({r["Trapped Attacker IP"] for r in rows}))
        else:
            st.info("No attacks captured yet. Honeypots are standing by.")
    time.sleep(3)
    st.rerun()
