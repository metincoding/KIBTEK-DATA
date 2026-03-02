import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Daire 6 Akıllı Panel", page_icon="🏠", layout="centered")

# --- TÜRKÇE AYARLAR ---
TR_AYLAR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
}

# Ev Sakinleri
EV_SAKINLERI = ["Metin", "Ev Arkadaşı 2", "Ev Arkadaşı 3", "Ev Arkadaşı 4"]

# Dinamik Değişkenler (Session State)
if 'kesinti_siniri' not in st.session_state:
    st.session_state['kesinti_siniri'] = 300

# --- GELİŞMİŞ CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; } 
    
    .status-card {
        background: linear-gradient(145deg, #1e1e1e, #141414);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #4CAF50;
        margin-bottom: 1rem;
    }
    
    .expense-card {
        background: linear-gradient(145deg, #161b22, #0d1117);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #2196F3;
        margin-bottom: 1rem;
    }

    .list-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px;
        border-bottom: 1px solid #222;
    }
    .text-green { color: #4CAF50; font-weight: bold; font-size: 1.1rem; }
    .text-blue { color: #2196F3; font-weight: bold; font-size: 1.1rem; }
    .text-muted { color: #888; font-size: 0.85rem; margin-top: 4px; }
    .buyer-badge { background:#2a2e33; padding:3px 8px; border-radius:12px; font-size:0.75rem; color:#bbb; margin-left:8px; }
    </style>
""", unsafe_allow_html=True)

# GÜVENLİK
DB_URL = st.secrets["DATABASE_URL"]

# --- VERİTABANI İŞLEMLERİ ---
@st.cache_data(ttl=300)
def load_energy_data():
    try:
        conn = psycopg2.connect(DB_URL)
        df = pd.read_sql_query("SELECT * FROM readings ORDER BY date_time ASC", conn)
        conn.close()
        if not df.empty:
            df['date_time'] = pd.to_datetime(df['date_time'])
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def load_expense_data():
    try:
        conn = psycopg2.connect(DB_URL)
        df = pd.read_sql_query("SELECT * FROM expenses ORDER BY date_time DESC", conn)
        conn.close()
        if not df.empty:
            df['date_time'] = pd.to_datetime(df['date_time'])
        return df
    except: return pd.DataFrame()

def add_expense(item, price, buyer):
    conn = psycopg2.connect(DB_URL)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO expenses (date_time, item_name, price, buyer) VALUES (%s, %s, %s, %s)", (now, item, price, buyer))
    conn.commit()
    c.close()
    conn.close()
    load_expense_data.clear()

def clear_table(table_name):
    conn = psycopg2.connect(DB_URL)
    c = conn.cursor()
    c.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY;")
    conn.commit()
    c.close()
    conn.close()
    load_expense_data.clear()
    load_energy_data.clear()

# ==========================================
# 🔐 ADMİN PANELİ (SİDEBAR)
# ==========================================
with st.sidebar:
    st.header("🛠️ Yönetim Paneli")
    
    if not st.session_state.get('admin_logged_in', False):
        st.write("Lütfen giriş yapın.")
        admin_user = st.text_input("Kullanıcı Adı")
        admin_pass = st.text_input("Şifre", type="password")
        
        if st.button("Giriş Yap", use_container_width=True):
            if admin_user == "admin" and admin_pass == "685600":
                st.session_state['admin_logged_in'] = True
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")
    else:
        st.success("Yönetici girişi aktif.")
        if st.button("Çıkış Yap", use_container_width=True):
            st.session_state['admin_logged_in'] = False
            st.rerun()
            
        st.divider()
        st.subheader("⚙️ Teknik Parametreler")
        # Dinamik olarak kesinti sınırını ayarlama
        yeni_sinir = st.number_input("Kesinti Sınırı (₺)", value=st.session_state['kesinti_siniri'], step=50)
        if st.button("Sınırı Güncelle", use_container_width=True):
            st.session_state['kesinti_siniri'] = yeni_sinir
            st.success("Güncellendi!")
            st.rerun()
            
        st.divider()
        st.subheader("🗑️ Veri Yönetimi")
        st.warning("Bu işlemler geri alınamaz!")
        
        if st.button("Tüm Harcamaları Sıfırla", type="primary", use_container_width=True):
            clear_table("expenses")
            st.success("Harcamalar silindi!")
            st.rerun()
            
        if st.button("Tüm Enerji Geçmişini Sıfırla", type="primary", use_container_width=True):
            clear_table("readings")
            st.success("Enerji verileri silindi!")
            st.rerun()

# --- VERİLERİ YÜKLE ---
df = load_energy_data()
df_exp = load_expense_data()

# ==========================================
# ⚡ 1. BÖLÜM: ENERJİ YÖNETİMİ
# ==========================================
st.title("🏠 Daire 6 Ortak Panel")

if not df.empty:
    KESINTI_SINIRI = st.session_state['kesinti_siniri']
    latest = df.iloc[-1]
    curr_bal = latest['balance']
    last_upd = latest['date_time']

    if curr_bal >= 4000: percent = 100.0
    elif curr_bal <= KESINTI_SINIRI: percent = 0.0
    else: percent = ((curr_bal - KESINTI_SINIRI) / (4000 - KESINTI_SINIRI)) * 100
    color = "#F44336" if percent < 15 else ("#FFC107" if percent < 40 else "#4CAF50")

    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_df = df[df['date_time'] >= seven_days_ago].copy()
    avg_daily = 0
    if len(recent_df) > 1:
        recent_df['diff_cons'] = recent_df['balance'].diff()
        drops = recent_df[recent_df['diff_cons'] < 0]['diff_cons'].abs()
        days = (recent_df['date_time'].max() - recent_df['date_time'].min()).days or 1
        avg_daily = drops.sum() / days

    one_day_ago = last_upd - timedelta(hours=24.5)
    last_24h_df = df[df['date_time'] >= one_day_ago].copy()
    last_24h_cons = 0
    if len(last_24h_df) > 1:
        last_24h_df['diff_cons'] = last_24h_df['balance'].diff()
        last_24h_cons = last_24h_df[last_24h_df['diff_cons'] < 0]['diff_cons'].abs().sum()

    usable_bal = max(0, curr_bal - KESINTI_SINIRI)
    days_left = usable_bal / avg_daily if avg_daily > 0 else 0
    finish_date = datetime.now() + timedelta(days=days_left)

    st.markdown(f"""
        <div style="background:#1a1a1a; border-radius:15px; padding:20px; border:1px solid #333;">
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="color:#aaa;">⚡ KIBTEK Enerji Bakiye</span>
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
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Son 24 Saat", f"{int(last_24h_cons)} ₺")
    with c2: st.metric("Günlük Ort.", f"{int(avg_daily)} ₺")
    with c3: st.metric("Tahmini Bitiş", f"{int(days_left)} Gün")
else:
    st.info("Sistemde henüz enerji verisi yok. Botun çalışması bekleniyor.")

st.write("---")

# ==========================================
# 🛒 2. BÖLÜM: ORTAK HARCAMALAR (EXPENSES)
# ==========================================
st.subheader("🛒 Ortak Ev Harcamaları")

with st.expander("➕ Yeni Harcama Ekle"):
    with st.form("expense_form", clear_on_submit=True):
        item_name = st.text_input("Alınan Ürün / Hizmet (Örn: Mutfak Alışverişi)")
        item_price = st.number_input("Toplam Tutar (₺)", min_value=0.0, format="%.2f", step=10.0)
        item_buyer = st.selectbox("Satın Alan Kişi", EV_SAKINLERI)
        
        submitted = st.form_submit_button("Listeye Ekle")
        
        if submitted:
            if item_name and item_price > 0:
                add_expense(item_name, item_price, item_buyer)
                st.success(f"{item_name}, {item_buyer} tarafından eklendi!")
                st.rerun() 
            else:
                st.warning("Lütfen ürün adı ve geçerli bir tutar girin.")

total_expense = df_exp['price'].sum() if not df_exp.empty else 0
per_person = total_expense / 4

st.markdown(f"""
    <div class="expense-card">
        <div style="color:#aaa; font-size:0.9rem;">Toplam Ev Harcaması</div>
        <div style="font-size:1.8rem; font-weight:bold; margin-top:5px;">{total_expense:,.2f} ₺</div>
        <div style="margin-top:10px; padding-top:10px; border-top:1px solid #333;">
            <span style="color:#888; font-size:0.9rem;">Kişi Başı Düşen (4 Kişi): </span>
            <span style="color:#2196F3; font-weight:bold; font-size:1.2rem;">{per_person:,.2f} ₺</span>
        </div>
    </div>
""", unsafe_allow_html=True)

if not df_exp.empty:
    st.markdown('<div style="background:#161b22; border-radius:12px; padding:5px;">', unsafe_allow_html=True)
    for _, row in df_exp.head(5).iterrows(): 
        buyer_name = row.get('buyer', 'Bilinmiyor')
        st.markdown(f"""
            <div class="list-item">
                <div>
                    <div style="font-weight:bold;">
                        {row['item_name']} 
                        <span class="buyer-badge">👤 {buyer_name}</span>
                    </div>
                    <div class="text-muted">{row['date_time'].day} {TR_AYLAR[row['date_time'].month]} {row['date_time'].year}</div>
                </div>
                <div class="text-blue">{row['price']:,.2f} ₺</div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Henüz ortak bir harcama girilmedi.")

# ==========================================
# 📈 3. BÖLÜM: GRAFİKLER VE DİĞERLERİ
# ==========================================
if not df.empty:
    st.write("---")
    with st.expander("📊 Enerji Bakiye Akışı ve Son Yüklemeler"):
        df['diff'] = df['balance'].diff()
        recharges = df[df['diff'] > 20].copy().sort_values(by='date_time', ascending=False)
        
        st.area_chart(df.set_index('date_time')['balance'], height=200)
        
        if not recharges.empty:
            st.markdown('**Son KIBTEK Yüklemeleri:**')
            for _, row in recharges.head(3).iterrows():
                st.markdown(f"- {row['date_time'].day} {TR_AYLAR[row['date_time'].month]}: **+{int(row['diff'])} ₺**")
