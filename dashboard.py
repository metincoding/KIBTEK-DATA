import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Enerji Tüketim Paneli", page_icon="⚡", layout="wide")

# --- KARANLIK TEMA VE ÖZEL CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #E0E0E0; }
    .metric-card { background-color: #1E1E1E; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-align: center; border: 1px solid #333; }
    .metric-title { font-size: 1.1rem; color: #A0A0A0; margin-bottom: 10px; }
    .metric-value { font-size: 2rem; font-weight: bold; color: #FFFFFF; }
    
    /* Kırmızı Yanıp Sönen Durum Kutusu Animasyonu */
    @keyframes blinkRed {
        0% { background-color: rgba(244, 67, 54, 1); box-shadow: 0 0 10px rgba(244,67,54,0.5); }
        50% { background-color: rgba(244, 67, 54, 0.4); box-shadow: 0 0 20px rgba(244,67,54,0.2); }
        100% { background-color: rgba(244, 67, 54, 1); box-shadow: 0 0 10px rgba(244,67,54,0.5); }
    }
    .offline-box {
        animation: blinkRed 1.5s infinite;
        padding: 15px;
        border-radius: 8px;
        color: white;
        text-align: center;
        font-weight: bold;
        margin-bottom: 20px;
        border: 1px solid #ffcccc;
    }
    </style>
""", unsafe_allow_html=True)

# GÜVENLİK: Streamlit Secrets üzerinden bağlantı adresini al
try:
    DB_URL = st.secrets["DATABASE_URL"]
except Exception:
    st.error("Veritabanı bağlantı adresi (DATABASE_URL) bulunamadı. Lütfen Streamlit Secrets ayarlarını kontrol edin.")
    st.stop()

@st.cache_data(ttl=600) # Veriyi 10 dakikada bir yenile (gereksiz DB sorgularını önler)
def load_data():
    try:
        conn = psycopg2.connect(DB_URL)
        query = "SELECT * FROM readings ORDER BY date_time ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        if not df.empty:
            df['date_time'] = pd.to_datetime(df['date_time'])
        return df
    except Exception as e:
        st.error(f"Veritabanı okuma hatası: {e}")
        return pd.DataFrame()

df = load_data()

st.markdown(f"## ⚡ Enerji Yönetim Paneli")

if df.empty:
    st.warning("Veritabanında gösterilecek veri yok. Scraper botunun çalışması bekleniyor.")
else:
    latest_record = df.iloc[-1]
    current_balance = latest_record['balance']
    last_update = latest_record['date_time']
    
    # --- ÇEVRİMDIŞI / GÜNCELLEME KONTROLÜ ---
    # Eğer son verinin üzerinden 12 saatten fazla geçmişse bot takılmış demektir.
    time_diff = datetime.now() - last_update
    if time_diff.total_seconds() > 43200: # 12 saat = 43200 saniye
        st.markdown("""
        <div class="offline-box">
            ⚠️ DİKKAT: Sistem Çevrimdışı! Son 12 saattir veri alınamıyor. Bot çalışmasını kontrol edin.
        </div>
        """, unsafe_allow_html=True)
        
    st.caption(f"Son Güncelleme: {last_update.strftime('%d.%m.%Y %H:%M')} | Hesap No: {latest_record['account_no']}")
    st.write("---")

    if current_balance >= 4000:
        percent = 100.0
        color = "#4CAF50" 
    elif current_balance <= 500:
        percent = (current_balance / 500) * 5.0
        color = "#F44336" 
    else:
        percent = 5 + ((current_balance - 500) / 3500) * 95
        color = "#FFC107" if percent < 50 else "#8BC34A" 

    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_df = df[df['date_time'] >= seven_days_ago].copy()
    
    avg_daily_consumption = 0
    estimated_days_left = 0

    if len(recent_df) > 1:
        recent_df['diff'] = recent_df['balance'].diff()
        consumption_drops = recent_df[recent_df['diff'] < 0]['diff'].abs()
        total_consumed = consumption_drops.sum()
        days_tracked = (recent_df['date_time'].max() - recent_df['date_time'].min()).days
        
        if days_tracked == 0:
            hours_tracked = (recent_df['date_time'].max() - recent_df['date_time'].min()).seconds / 3600
            if hours_tracked > 0:
                avg_daily_consumption = (total_consumed / hours_tracked) * 24
        else:
            avg_daily_consumption = total_consumed / days_tracked

    if avg_daily_consumption > 0:
        estimated_days_left = current_balance / avg_daily_consumption

    battery_html = f"""
    <div style="display: flex; align-items: center; justify-content: center; margin: 30px 0;">
        <div style="width: 80%; height: 60px; border: 4px solid #555; border-radius: 12px; position: relative; background-color: #222;">
            <div style="position: absolute; right: -16px; top: 12px; width: 12px; height: 28px; background-color: #555; border-radius: 0 6px 6px 0;"></div>
            <div style="width: {percent}%; height: 100%; background-color: {color}; border-radius: 8px; transition: width 1s ease-in-out;"></div>
            <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-family: sans-serif; font-weight: bold; font-size: 1.5rem; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.8);">
                {int(current_balance)} TRY ({percent:.1f}%)
            </div>
        </div>
    </div>
    """
    st.markdown(battery_html, unsafe_allow_html=True)
    st.write("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Kalan Bakiye</div><div class="metric-value" style="color: {color};">{int(current_balance)} ₺</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Ortalama Günlük Tüketim</div><div class="metric-value">{int(avg_daily_consumption)} ₺ / Gün</div></div>', unsafe_allow_html=True)
    with col3:
        days_color = "#F44336" if estimated_days_left < 3 else "#FFFFFF"
        st.markdown(f'<div class="metric-card"><div class="metric-title">Tahmini Kalan Süre</div><div class="metric-value" style="color: {days_color};">{int(estimated_days_left) if estimated_days_left > 0 else "---"} Gün</div></div>', unsafe_allow_html=True)

    st.write("---")
    st.markdown("### Geçmiş Tüketim Trendi")
    chart_df = df[['date_time', 'balance']].set_index('date_time')
    st.line_chart(chart_df, use_container_width=True)