import streamlit as st, pyotp, time, os, pandas as pd
st.set_page_config(page_title="MTD Dashboard", layout="wide")
totp = pyotp.TOTP('JBSWY3DPEHPK3PXP', interval=30)

st.title("🛡️ Chrono-Chameleon Defense Dashboard")
col1, col2 = st.columns(2)
with col1:
    st.header("🟢 Active Application Port")
    st.metric(label="Secure Port", value=8000 + (int(totp.now()) % 50))
with col2:
    st.header("🚨 Banned Hackers")
    if os.path.exists("shared_logs/attack.log") and os.path.getsize("shared_logs/attack.log") > 0:
        df = pd.read_csv("shared_logs/attack.log", names=["Time", "IP", "Port"])
        st.dataframe(df.tail(10))
    else:
        st.success("No attacks detected yet.")
time.sleep(2)
st.rerun()
