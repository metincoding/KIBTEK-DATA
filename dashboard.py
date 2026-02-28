import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="KIBTEK Mobil Panel", page_icon="⚡", layout="centered")

# --- TÜRKÇE AYARLAR ---
TR_AYLAR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
}

# --- GELİŞMİŞ CSS (Mobil Odaklı) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    
    /* Metrikleri mobil ekrana 3 sütun sığdırmak için fontu biraz kısalttık */
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; } 
    
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
recharges = df[df['diff'] > 20].copy().sort_values(by='date_time', ascending=False)

# 2. TÜKETİM ANALİZİ (Son 7 Gün)
seven_days_ago = datetime.now() - timedelta(days=7)
recent_df = df[df['date_time'] >= seven_days_ago].copy()
avg_daily = 0
if len(recent_df) > 1:
    recent_df['diff_cons'] = recent_df['balance'].diff()
    drops = recent_df[recent_df['diff_cons'] < 0]['diff_cons'].abs()
    days = (recent_df['date_time'].max() - recent_df['date_time'].min()).days or 1
    avg_daily = drops.sum() / days

# 3. SON 24 SAAT TÜKETİMİ
# Bot bir-iki dakika geç tetiklenebileceği için 24.5 saatlik toleranslı bir aralık alıyoruz
one_day_ago = last_upd - timedelta(hours=24.5)
last_24h_df = df[df['date_time'] >= one_day_ago].copy()
last_24h_cons = 0
if len(last_24h_df) > 1:
    last_24h_df['diff_cons'] = last_24h_df['balance'].diff()
    # Yalnızca düşüşleri (tüketimi) topla, araya yükleme girdiyse onu sayma
    last_24h_cons = last_24h_df[last_24h_df['diff_cons'] < 0]['diff_cons'].abs().sum()

# 4. STRATEJİK HESAPLAMALAR
usable_bal = max(0, curr_bal - KESINTI_SINIRI)
days_left = usable_bal / avg_daily if avg_daily > 0 else 0
finish_date = datetime.now() + timedelta(days=days_left)
weekly_cost = avg_daily * 7

# --- UI BAŞLANGIÇ ---
st.title("⚡ Daire 6")

# Pil ve Ana Bakiye
if curr_bal >= 4000: percent = 100.0
elif curr_bal <= KESINTI_SINIRI: percent = 0.0
else: percent = ((curr_bal - KESINTI_SINIRI) / (4000 - KESINTI_SINIRI)) * 100
color = "#F44336" if percent < 15 else ("#FFC107" if percent < 40 else "#4CAF50")

st.markdown(f"""
    <div style="background:#1a1a1a; border-radius:15px; padding:20px; border:1px solid #333;">
        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <span style="color:#aaa;">Kullanılabilir Enerji</span>
            <span style="font-weight:bold; color:{color};">%{percent:.1f}</span>
        </div>
        <div style="width:100%; height:25px; background:#333; border-radius:20px; overflow:hidden;">
            <div style="width:{percent}%; height:100%; background:{color}; transition:1s;"></div>
        </div>
        <div style="margin-top:15px; font-size:2rem; font-weight:bold;">{int(curr_bal)} ₺</div>
        <div style="color:#666; font-size:0.8rem;">Güncelleme: {last_upd.strftime('%H:%M')} | {last_upd.day} {TR_AYLAR[last_upd.month]}</div>
    </div>
""", unsafe_allow_html=True)

st.write("")

# Tahmin Kartı (Türkçe Tarihli)
st.markdown(f"""
    <div class="status-card" style="border-left-color: {color};">
        <div style="color:#aaa; font-size:0.9rem;">Tahmini Kesinti ({KESINTI_SINIRI} ₺ Altı)</div>
        <div style="font-size:1.4rem; font-weight:bold; margin-top:5px;">
            {finish_date.day} {TR_AYLAR[finish_date.month]} {finish_date.year}
        </div>
        <div style="color:{color}; font-size:0.8rem;">Yaklaşık {int(days_left)} gün sonra</div>
    </div>
""", unsafe_allow_html=True)

# METRİKLER (3 Sütun)
c1, c2, c3 = st.columns(3)
with c1: st.metric("Son 24 Saat", f"{int(last_24h_cons)} ₺")
with c2: st.metric("Günlük Ort.", f"{int(avg_daily)} ₺")
with c3: st.metric("Haftalık Harc.", f"{int(weekly_cost)} ₺")

# --- SON YÜKLEMELER KARTI (Türkçe Tarihli) ---
st.write("")
st.subheader("💰 Son Yüklemeler")
if not recharges.empty:
    with st.container():
        st.markdown('<div style="background:#161b22; border-radius:12px; padding:5px;">', unsafe_allow_html=True)
        for _, row in recharges.head(5).iterrows(): 
            st.markdown(f"""
                <div class="recharge-item">
                    <div>
                        <div style="font-weight:bold;">KIBTEK Yükleme</div>
                        <div class="recharge-date">
                            {row['date_time'].day} {TR_AYLAR[row['date_time'].month]}, {row['date_time'].strftime('%H:%M')}
                        </div>
                    </div>
                    <div class="recharge-amount">+{int(row['diff'])} ₺</div>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Henüz bir yükleme hareketi tespit edilmedi.")

# Grafik
st.write("")
st.subheader("Bakiye Akışı")
st.area_chart(df.set_index('date_time')['balance'], height=200)

st.caption(f"Hesap No: {latest['account_no']} | Otomatik Hareket Analizi")
