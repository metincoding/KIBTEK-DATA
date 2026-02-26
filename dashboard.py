import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="KIBTEK Mobil Panel", page_icon="⚡", layout="centered")

# --- GELİŞMİŞ CSS (Mobil Odaklı) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    
    .status-card {
        background: linear-gradient(145deg, #1e1e1e, #141414);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #4CAF50;
        margin-bottom: 1rem;
    }

    /* Yükleme Listesi Stili */
    .recharge-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px;
        border-bottom: 1px solid #222;
    }
    .recharge-amount {
        color: #4CAF50;
        font-weight: bold;
        font-size: 1.1rem;
    }
    .recharge-date {
        color: #888;
        font-size: 0.85rem;
    }
    
    @keyframes blinkRed {
        0% { background-color: rgba(244, 67, 54, 0.8); }
        50% { background-color: rgba(244, 67, 54, 0.2); }
        100% { background-color: rgba(244, 67, 54, 0.8); }
    }
    .offline-box {
        animation: blinkRed 2s infinite;
        padding: 12px;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
        font-size: 0.9rem;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# GÜVENLİK
DB_URL = st.secrets["DATABASE_URL"]

@st.cache_data(ttl=300)
def load_data():
    try:
        conn = psycopg2.connect(DB_URL)
        df = pd.read_sql_query("SELECT * FROM readings ORDER BY date_time ASC", conn)
        conn.close()
        df['date_time'] = pd.to_datetime(df['date_time'])
        return df
    except: return pd.DataFrame()

df = load_data()

if df.empty:
    st.error("Veri bulunamadı.")
    st.stop()

# --- AYARLAR VE ANALİZ ---
KESINTI_SINIRI = 300 
latest = df.iloc[-1]
curr_bal = latest['balance']
last_upd = latest['date_time']

# 1. YÜKLEME TESPİT MANTIĞI
df['diff'] = df['balance'].diff()
# Eğer fark 20 TL'den büyükse yükleme olarak kabul et (ufak dalgalanmaları elemek için)
recharges = df[df['diff'] > 20].copy().sort_values(by='date_time', ascending=False)

# 2. TÜKETİM ANALİZİ
seven_days_ago = datetime.now() - timedelta(days=7)
recent_df = df[df['date_time'] >= seven_days_ago].copy()
avg_daily = 0
if len(recent_df) > 1:
    recent_df['diff_cons'] = recent_df['balance'].diff()
    drops = recent_df[recent_df['diff_cons'] < 0]['diff_cons'].abs()
    days = (recent_df['date_time'].max() - recent_df['date_time'].min()).days or 1
    avg_daily = drops.sum() / days

# 3. STRATEJİK HESAPLAMALAR
usable_bal = max(0, curr_bal - KESINTI_SINIRI)
days_left = usable_bal / avg_daily if avg_daily > 0 else 0
finish_date = datetime.now() + timedelta(days=days_left)
weekly_cost = avg_daily * 7
