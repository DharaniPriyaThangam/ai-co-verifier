# app.py
import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO
from datetime import datetime


st.set_page_config(page_title="AI CO Verifier")

# TEMP TEST OUTPUT
st.title("✅ AI-Based CO Verifier")
st.write("If you see this, your app is working!")


# --- Database Setup ---
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS upload_logs (
                    username TEXT,
                    timestamp TEXT,
                    filename TEXT
                )''')
    conn.commit()
    conn.close()

def add_user(username, password, role="faculty"):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

def authenticate(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# --- Bloom Level Classifier ---
def classify_blooms_level(question):
    question = question.lower()
    blooms_keywords = {
        "Remember": ["define", "list", "name", "identify", "recall"],
        "Understand": ["explain", "describe", "summarize", "interpret", "classify"],
        "Apply": ["solve", "use", "demonstrate", "compute", "execute"],
        "Analyze": ["compare", "analyze", "differentiate", "examine", "investigate"],
        "Evaluate": ["evaluate", "justify", "critique", "assess", "argue"],
        "Create": ["design", "develop", "formulate", "construct", "propose"]
    }
    for level, keywords in blooms_keywords.items():
        for keyword in keywords:
            if keyword in question:
                return level
    return "Not Classified"

# --- CO Matcher ---
def match_course_outcome(question):
    question = question.lower()
    co_keywords = {
        "CO1": ["define", "list", "identify"],
        "CO2": ["explain", "describe", "summarize"],
        "CO3": ["solve", "use", "apply"],
        "CO4": ["analyze", "compare", "differentiate"],
        "CO5": ["evaluate", "justify", "assess"],
        "CO6": ["design", "develop", "construct"]
    }
    for co, keywords in co_keywords.items():
        if any(keyword in question for keyword in keywords):
            return co
    return "CO Not Found"

# --- Initialize DB ---
init_db()

# --- Login System ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

if not st.session_state.logged_in:
    st.title(" Faculty Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        role = authenticate(username, password)
        if role:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = role
            st.success(f"Welcome {username}!")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")
else:
    st.sidebar.title("👋 Welcome")
    st.sidebar.write(f"Logged in as: {st.session_state.username} ({st.session_state.role})")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

    st.title("🧠 AI-Based CO & Bloom's Verifier")
    uploaded_file = st.file_uploader("📄 Upload Question Paper CSV", type="csv")

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        if "Question" not in df.columns:
            st.error("CSV must contain a 'Question' column.")
        else:
            df["Bloom’s Level"] = df["Question"].apply(classify_blooms_level)
            df["Matched CO"] = df["Question"].apply(match_course_outcome)
            st.dataframe(df)

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name="CO Report")
            st.download_button("📥 Download Report", data=buffer.getvalue(), file_name="CO_Blooms_Report.xlsx")

            # Log upload
            conn = sqlite3.connect("users.db")
            c = conn.cursor()
            c.execute("INSERT INTO upload_logs (username, timestamp, filename) VALUES (?, ?, ?)",
                      (st.session_state.username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uploaded_file.name))
            conn.commit()
            conn.close()

    if st.session_state.role == "admin":
        st.subheader("👨‍💼 Admin Dashboard")
        conn = sqlite3.connect("users.db")
        c = conn.cursor()

        st.markdown("### ➕ Add Faculty User")
        new_user = st.text_input("New Faculty Username")
        new_pass = st.text_input("Password", type="password")
        if st.button("Add Faculty"):
            add_user(new_user, new_pass)
            st.success("User added.")

        st.markdown("### 📜 Upload Log History")
        logs = pd.read_sql_query("SELECT * FROM upload_logs", conn)
        st.dataframe(logs)
        conn.close()
