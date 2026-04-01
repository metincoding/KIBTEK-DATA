import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Daire 6 Pro", page_icon="🏠", layout="centered")

TR_AYLAR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}

# CSS ve Animasyonlar
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .announcement-box { background: linear-gradient(90deg, #ff8a00, #e52e71); padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 20px; color: white; }
    .status-card { background: #1e1e1e; padding: 1.5rem; border-radius: 15px; border-left: 5px solid #4CAF50; margin-bottom: 1rem; }
    .list-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #222; }
    </style>
""", unsafe_allow_html=True)

# Veritabanı Yardımcı Fonksiyonu
def run_query(query, params=(), is_select=True):
    try:
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute(query, params)
        if is_select:
            cols = [desc[0] for desc in cur.description]
            res = pd.DataFrame(cur.fetchall(), columns=cols)
            conn.close()
            return res
        conn.commit()
        conn.close()
    except Exception as e:
        return pd.DataFrame()

# Oturum Yönetimi
if 'user' not in st.session_state: st.session_state.user = None

# ==========================================
# 🔐 SIDEBAR: GİRİŞ PANELİ
# ==========================================
with st.sidebar:
    if st.session_state.user is None:
        st.subheader("🔑 Üye Girişi")
        u_name = st.text_input("Kullanıcı Adı")
        u_pass = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap", use_container_width=True):
            user_check = run_query("SELECT * FROM users WHERE username = %s AND password = %s", (u_name, u_pass))
            if not user_check.empty:
                st.session_state.user = user_check.iloc[0].to_dict()
                st.rerun()
            else: st.error("Hatalı bilgiler!")
    else:
        st.success(f"Oturum: {st.session_state.user['username']}")
        if st.button("Çıkış Yap", use_container_width=True):
            st.session_state.user = None
            st.rerun()

# ==========================================
# 📊 ANA SAYFA (READ-ONLY INDEX)
# ==========================================
st.title("⚡ Daire 6 Ortak Panel")

# 1. ENERJİ DURUMU (Herkes Görebilir)
df_energy = run_query("SELECT * FROM readings ORDER BY date_time ASC")
if not df_energy.empty:
    latest = df_energy.iloc[-1]
    curr_bal = float(latest['balance'])
    st.metric("Güncel KIBTEK Bakiyesi", f"{int(curr_bal)} ₺")
    st.progress(min(1.0, max(0.0, (curr_bal - 300) / 3700)))

# 2. BORÇ DURUMU (Herkes Görebilir)
st.subheader("⚖️ Güncel Borç/Alacak Durumu")
all_payments = run_query("""
    SELECT p.*, u.username as payer_name, r.username as receiver_name 
    FROM payments p 
    JOIN users u ON p.payer_id = u.id 
    JOIN users r ON p.receiver_id = r.id 
    WHERE p.status != 'paid'
""")

if not all_payments.empty:
    for _, row in all_payments.iterrows():
        status_text = "⏳ Onay Bekliyor" if row['status'] == 'pending_approval' else "🔴 Ödeme Bekleniyor"
        st.markdown(f"<div class='list-item'><div><b>{row['payer_name']}</b> ➔ {row['receiver_name']}</div><div>{row['amount']} ₺ <small>({status_text})</small></div></div>", unsafe_allow_html=True)
else:
    st.success("Tüm ödemeler tamamlanmış! 🎉")

# ==========================================
# 🛠️ YETKİLİ İŞLEMLER (SADECE GİRİŞ YAPINCA)
# ==========================================
if st.session_state.user:
    st.divider()
    st.subheader(f"🛠️ İşlemler ({st.session_state.user['username']})")
    
    tab1, tab2, tab3 = st.tabs(["➕ Harcama Ekle", "💸 Borçlarım", "✅ Onaylarım"])

    with tab1:
        with st.form("exp_form"):
            item = st.text_input("Ne alındı?")
            price = st.number_input("Tutar", min_value=0.0)
            if st.form_submit_button("Kaydet ve Paylaştır"):
                # Harcamayı ekle ve borçları oluştur (Basitleştirilmiş mantık)
                res = run_query("INSERT INTO expenses (item_name, price, buyer, date_time) VALUES (%s, %s, %s, NOW()) RETURNING id", (item, price, st.session_state.user['username']), is_select=True)
                # Borç dağıtım mantığı SQL tetikleyicisi veya burada döngü ile kurulabilir
                st.success("Harcama kaydedildi.")
                st.rerun()

    with tab2:
        # Kişinin kendi borçlarını "Ödedim" olarak işaretlemesi
        st.write("Ödediğiniz borçları buradan bildirin.")

    with tab3:
        # Kişinin kendisine yapılan ödemeleri onaylaması
        st.write("Gelen ödemeleri buradan onaylayın.")
else:
    st.info("💡 Veri eklemek veya ödeme onaylamak için lütfen giriş yapın.")
