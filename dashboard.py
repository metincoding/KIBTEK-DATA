import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Daire 6 Pro", page_icon="🏠", layout="centered")

TR_AYLAR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}

# EV SAKİNLERİ
EV_SAKINLERI = ["Metin", "Zafer", "Murat", "Mehmet"]

if 'user' not in st.session_state: st.session_state.user = None
if 'buy_item_id' not in st.session_state: st.session_state['buy_item_id'] = None

# --- GELİŞMİŞ CSS & ANİMASYON ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .status-card { background: #1e1e1e; padding: 1.2rem; border-radius: 12px; border-left: 5px solid #4CAF50; margin-bottom: 1rem; }
    .list-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #222; background: #161b22; margin-bottom: 5px; border-radius: 8px; }
    
    @keyframes moveStripes { 0% { background-position: 0 0; } 100% { background-position: 40px 0; } }
    .energy-bar-fill {
        background-image: linear-gradient(45deg, rgba(255,255,255,0.15) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.15) 50%, rgba(255,255,255,0.15) 75%, transparent 75%, transparent);
        background-size: 40px 40px; animation: moveStripes 1s linear infinite; border-radius: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- VERİTABANI: TEK BAĞLANTILI İŞLEM (HATA ÇÖZÜMÜ) ---
def run_query(query, params=(), is_select=True):
    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        if is_select:
            cols = [desc[0] for desc in cur.description]
            res = pd.DataFrame(cur.fetchall(), columns=cols)
            return res
        conn.commit()
    except Exception as e:
        st.error(f"Sorgu Hatası: {e}")
        conn.rollback()
    finally:
        conn.close()

# --- SIDEBAR ---
with st.sidebar:
    if st.session_state.user is None:
        st.subheader("🔑 Giriş")
        u_name = st.text_input("İsim")
        u_pass = st.text_input("Şifre", type="password")
        if st.button("Giriş", use_container_width=True):
            user_check = run_query("SELECT * FROM users WHERE username = %s AND password = %s", (u_name, u_pass))
            if user_check is not None and not user_check.empty:
                st.session_state.user = user_check.iloc[0].to_dict()
                st.rerun()
    else:
        st.success(f"Oturum: {st.session_state.user['username']}")
        if st.button("Çıkış", use_container_width=True):
            st.session_state.user = None
            st.rerun()

# --- VERİLERİ YÜKLE ---
df_energy = run_query("SELECT * FROM readings ORDER BY date_time ASC")
if df_energy is not None and not df_energy.empty:
    df_energy['balance'] = pd.to_numeric(df_energy['balance'], errors='coerce') # GRAFİK DÜZELTME
    df_energy['date_time'] = pd.to_datetime(df_energy['date_time'])

df_exp = run_query("SELECT * FROM expenses ORDER BY date_time DESC")
df_shop = run_query("SELECT * FROM shopping_list ORDER BY date_added DESC")
try: df_ann = run_query("SELECT message FROM announcements LIMIT 1")
except: df_ann = pd.DataFrame()

# ==========================================
# 📊 ANA SAYFA (İNDEKS)
# ==========================================
st.title("⚡ Daire 6 Ortak Panel")

if not df_energy.empty:
    curr_bal = float(df_energy.iloc[-1]['balance'])
    last_upd = df_energy.iloc[-1]['date_time']
    percent = max(0.0, min(100.0, ((curr_bal - 300) / 3700) * 100))
    color = "#F44336" if percent < 15 else ("#FFC107" if percent < 40 else "#4CAF50")

    # Analizler
    recent_df = df_energy[df_energy['date_time'] >= (datetime.now() - timedelta(days=7))].copy()
    avg_daily = recent_df[recent_df['balance'].diff() < 0]['balance'].diff().abs().sum() / max(1, (recent_df['date_time'].max() - recent_df['date_time'].min()).days) if len(recent_df) > 1 else 0
    
    # HATA DÜZELTME: days_left tam sayıya zorlandı
    days_left = int(max(0, curr_bal - 300) / avg_daily) if avg_daily > 0 else 0
    kesinti_tarihi = datetime.now() + timedelta(days=days_left)

    st.markdown(f"""
        <div style="background:#1a1a1a; border-radius:15px; padding:20px; border:1px solid #333;">
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="color:#aaa;">⚡ Enerji Durumu</span>
                <span style="font-weight:bold; color:{color};">%{percent:.1f}</span>
            </div>
            <div style="width:100%; height:25px; background:#333; border-radius:20px; overflow:hidden;">
                <div class="energy-bar-fill" style="width:{percent}%; height:100%; background-color:{color};"></div>
            </div>
            <div style="margin-top:15px; font-size:2rem; font-weight:bold;">{int(curr_bal)} ₺</div>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Günlük Ort.", f"{int(avg_daily)} ₺")
    with c2: st.metric("Kesinti Tahmini", f"{kesinti_tarihi.day} {TR_AYLAR[kesinti_tarihi.month]}")
    with c3: st.metric("Kalan", f"{days_left} Gün")

st.divider()

# BORÇ DURUMU (Özet)
st.subheader("⚖️ Güncel Borç/Alacak Durumu")
all_payments = run_query("""
    SELECT p.*, u.username as payer_name, r.username as receiver_name 
    FROM payments p 
    JOIN users u ON p.payer_id = u.id 
    JOIN users r ON p.receiver_id = r.id 
    WHERE p.status != 'paid'
""")

if all_payments is not None and not all_payments.empty:
    for _, row in all_payments.iterrows():
        status = "🔴 Bekliyor" if row['status'] == 'pending_payment' else "⏳ Onayda"
        st.markdown(f"<div class='list-item'><div><b>{row['payer_name']}</b> ➔ {row['receiver_name']}</div><div>{row['amount']} ₺ ({status})</div></div>", unsafe_allow_html=True)
else:
    st.success("Herkes ödeşmiş, borç yok! ✨")

# ==========================================
# 🔐 YETKİLİ İŞLEMLER
# ==========================================
if st.session_state.user:
    st.divider()
    st.subheader(f"🛠️ İşlemler: {st.session_state.user['username']}")
    t1, t2, t3 = st.tabs(["➕ Harcama", "💸 Borçlarım", "✅ Onaylarım"])

    with t1:
        with st.form("new_exp"):
            item = st.text_input("Ürün Adı")
            price = st.number_input("Toplam Fiyat", min_value=0.0)
            if st.form_submit_button("Kaydet ve 4'e Böl"):
                if item and price > 0:
                    # FK Hatasını çözmek için tek bağlantıda iki işlem yapıyoruz
                    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
                    cur = conn.cursor()
                    try:
                        cur.execute("INSERT INTO expenses (item_name, price, buyer, date_time) VALUES (%s, %s, %s, NOW()) RETURNING id", (item, price, st.session_state.user['username']))
                        exp_id = cur.fetchone()[0]
                        
                        share = price / 4
                        for name in EV_SAKINLERI:
                            if name != st.session_state.user['username']:
                                cur.execute("INSERT INTO payments (expense_id, payer_id, receiver_id, amount) VALUES (%s, (SELECT id FROM users WHERE username=%s), (SELECT id FROM users WHERE username=%s), %s)", (exp_id, name, st.session_state.user['username'], share))
                        conn.commit()
                        st.success("Harcama ve borçlar işlendi!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")
                        conn.rollback()
                    finally: conn.close()

# ==========================================
# 📊 ENERJİ GRAFİĞİ VE YÜKLEMELER
# ==========================================
st.write("---")
st.subheader("📈 Enerji Grafiği ve Yüklemeler")
if not df_energy.empty:
    st.area_chart(df_energy.set_index('date_time')['balance'], height=200) # DÜZELTİLDİ
    
    df_energy['diff'] = df_energy['balance'].diff()
    recharges = df_energy[df_energy['diff'] > 20].copy().sort_values(by='date_time', ascending=False)
    if not recharges.empty:
        for _, row in recharges.head(3).iterrows():
            st.markdown(f"✅ **{row['date_time'].day} {TR_AYLAR[row['date_time'].month]}**: +{int(row['diff'])} ₺ Yükleme")
