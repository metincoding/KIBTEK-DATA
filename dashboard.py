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
KESINTI_SINIRI = 300 # Kullanıcının belirttiği kritik kesinti sınırı
latest = df.iloc[-1]
curr_bal = latest['balance']
last_upd = latest['date_time']

# Pil Hesaplama (300 TRY = %0, 4000 TRY+ = %100)
if curr_bal >= 4000: 
    percent = 100.0
elif curr_bal <= KESINTI_SINIRI:
    percent = 0.0
else:
    # 300 ile 4000 arasını %0 ile %100 arasına oranla
    percent = ((curr_bal - KESINTI_SINIRI) / (4000 - KESINTI_SINIRI)) * 100

color = "#F44336" if percent < 15 else ("#FFC107" if percent < 40 else "#4CAF50")

# Tüketim Analizi (Son 7 Gün)
seven_days_ago = datetime.now() - timedelta(days=7)
recent_df = df[df['date_time'] >= seven_days_ago].copy()
avg_daily = 0
if len(recent_df) > 1:
    recent_df['diff'] = recent_df['balance'].diff()
    drops = recent_df[recent_df['diff'] < 0]['diff'].abs()
    days = (recent_df['date_time'].max() - recent_df['date_time'].min()).days or 1
    avg_daily = drops.sum() / days

# Stratejik Hesaplamalar (Kullanılabilir bakiye üzerinden)
usable_bal = max(0, curr_bal - KESINTI_SINIRI)
days_left = usable_bal / avg_daily if avg_daily > 0 else 0
finish_date = datetime.now() + timedelta(days=days_left)
weekly_cost = avg_daily * 7

# --- UI BAŞLANGIÇ ---
st.title("⚡ Daire 6")

# Offline Kontrolü
if (datetime.now() - last_upd).total_seconds() > 43200:
    st.markdown('<div class="offline-box">⚠️ SİSTEM ÇEVRİMDIŞI (12+ Saat)</div>', unsafe_allow_html=True)

# Pil Göstergesi
st.markdown(f"""
    <div style="background:#1a1a1a; border-radius:15px; padding:15px; border:1px solid #333;">
        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <span style="color:#aaa;">Kullanılabilir Enerji</span>
            <span style="font-weight:bold; color:{color};">%{percent:.1f}</span>
        </div>
        <div style="width:100%; height:25px; background:#333; border-radius:20px; overflow:hidden;">
            <div style="width:{percent}%; height:100%; background:{color}; transition:1s;"></div>
        </div>
        <div style="margin-top:10px; font-size:1.5rem; font-weight:bold;">{int(curr_bal)} ₺</div>
        <div style="color:#666; font-size:0.8rem;">Eşik: {KESINTI_SINIRI} ₺ | Güncelleme: {last_upd.strftime('%H:%M | %d.%m')}</div>
    </div>
""", unsafe_allow_html=True)

st.write("")

# Metrikler
c1, c2 = st.columns(2)
with c1:
    st.metric("Günlük Ort. Tüketim", f"{int(avg_daily)} ₺")
with c2:
    st.metric("Haftalık Tahmin", f"{int(weekly_cost)} ₺")

# Stratejik Kart
st.markdown(f"""
    <div class="status-card" style="border-left-color: {color};">
        <div style="color:#aaa; font-size:0.9rem;">Tahmini Kesinti Tarihi ({KESINTI_SINIRI} ₺ Altı)</div>
        <div style="font-size:1.4rem; font-weight:bold; margin-top:5px;">
            {finish_date.strftime('%d %B %Y')}
        </div>
        <div style="color:{color}; font-size:0.8rem; margin-top:3px;">
            Yaklaşık {int(days_left)} gün sonra
        </div>
    </div>
""", unsafe_allow_html=True)

# Grafik
st.subheader("Bakiye Akışı")
st.area_chart(df.set_index('date_time')['balance'], height=200)

st.caption(f"Hesap No: {latest['account_no']} | Kesinti Eşiği Dikkate Alınmıştır")

