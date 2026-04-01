import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Daire 6 Pro", page_icon="🏠", layout="centered")

TR_AYLAR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}

# CSS Tasarımı
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .status-card { background: #1e1e1e; padding: 1.2rem; border-radius: 12px; border-left: 5px solid #4CAF50; margin-bottom: 1rem; }
    .list-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #222; background: #161b22; margin-bottom: 5px; border-radius: 8px; }
    .pending-badge { background: #ff9800; color: black; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: bold; }
    .approval-badge { background: #2196F3; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Veritabanı Fonksiyonu
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
    finally:
        conn.close()

# Oturum Yönetimi
if 'user' not in st.session_state: st.session_state.user = None

# --- SIDEBAR ---
with st.sidebar:
    if st.session_state.user is None:
        st.subheader("🔑 Giriş")
        u_name = st.text_input("İsim")
        u_pass = st.text_input("Şifre", type="password")
        if st.button("Giriş", use_container_width=True):
            user_check = run_query("SELECT * FROM users WHERE username = %s AND password = %s", (u_name, u_pass))
            if not user_check.empty:
                st.session_state.user = user_check.iloc[0].to_dict()
                st.rerun()
            else: st.error("Hatalı!")
    else:
        st.success(f"Kullanıcı: {st.session_state.user['username']}")
        if st.button("Çıkış", use_container_width=True):
            st.session_state.user = None
            st.rerun()

# ==========================================
# 📊 ANA SAYFA (HERKESE AÇIK)
# ==========================================
st.title("⚡ Daire 6 Ortak Panel")

# 1. BORÇ DURUMU (ANA TABLO)
st.subheader("⚖️ Güncel Borç/Alacak Listesi")
all_payments = run_query("""
    SELECT p.*, u.username as payer_name, r.username as receiver_name, e.item_name 
    FROM payments p 
    JOIN users u ON p.payer_id = u.id 
    JOIN users r ON p.receiver_id = r.id 
    JOIN expenses e ON p.expense_id = e.id
    WHERE p.status != 'paid'
""")

if not all_payments.empty:
    for _, row in all_payments.iterrows():
        badge = '<span class="approval-badge">⏳ Onay Bekliyor</span>' if row['status'] == 'pending_approval' else '<span class="pending-badge">🔴 Ödeme Bekleniyor</span>'
        st.markdown(f"""
            <div class='list-item'>
                <div>
                    <b>{row['payer_name']}</b> ➔ {row['receiver_name']}<br>
                    <small style='color:#888'>{row['item_name']}</small>
                </div>
                <div style='text-align:right'>
                    <b>{row['amount']:.2f} ₺</b><br>
                    {badge}
                </div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.success("Tüm ödemeler tamamlanmış! Tertemiz sayfa. 😇")

# ==========================================
# 🔐 YETKİLİ ALAN (GİRİŞ ŞART)
# ==========================================
if st.session_state.user:
    st.divider()
    t1, t2, t3 = st.tabs(["➕ Harcama Ekle", "💸 Borçlarım", "✅ Onaylarım"])

    with t1:
        with st.form("add_exp", clear_on_submit=True):
            item = st.text_input("Ürün/Hizmet Adı")
            price = st.number_input("Toplam Fiyat", min_value=0.0)
            if st.form_submit_button("Kaydet ve 4'e Böl"):
                if item and price > 0:
                    # 1. Harcamayı Kaydet
                    res = run_query("INSERT INTO expenses (item_name, price, buyer, date_time) VALUES (%s, %s, %s, NOW()) RETURNING id", 
                                    (item, price, st.session_state.user['username']), is_select=True)
                    exp_id = int(res.iloc[0]['id'])
                    
                    # 2. Borçları Dağıt (Ödeyen hariç herkese 1/4 borç yaz)
                    share = price / 4
                    other_users = run_query("SELECT id FROM users WHERE username != %s", (st.session_state.user['username'],))
                    for _, u in other_users.iterrows():
                        run_query("INSERT INTO payments (expense_id, payer_id, receiver_id, amount, status) VALUES (%s, %s, %s, %s, 'pending_payment')", 
                                  (exp_id, int(u['id']), st.session_state.user['id'], share), is_select=False)
                    st.success("Harcama ve borçlar işlendi!")
                    st.rerun()

    with t2:
        # Kişinin başkasına olan borçları
        my_debts = run_query("""
            SELECT p.*, e.item_name, r.username as receiver_name 
            FROM payments p 
            JOIN expenses e ON p.expense_id = e.id 
            JOIN users r ON p.receiver_id = r.id 
            WHERE p.payer_id = %s AND p.status = 'pending_payment'
        """, (st.session_state.user['id'],))
        
        if not my_debts.empty:
            for _, d in my_debts.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"🛒 {d['item_name']} ({d['receiver_name']}'e) - **{d['amount']:.2f} ₺**")
                if c2.button("Ödedim ✅", key=f"d_{d['id']}"):
                    run_query("UPDATE payments SET status = 'pending_approval' WHERE id = %s", (int(d['id']),), is_select=False)
                    st.rerun()
        else: st.write("Ödenmesi gereken borcun yok. 😎")

    with t3:
        # Kişinin başkasından alacağı ve onaylaması gereken ödemeler
        my_apps = run_query("""
            SELECT p.*, e.item_name, u.username as payer_name 
            FROM payments p 
            JOIN expenses e ON p.expense_id = e.id 
            JOIN users u ON p.payer_id = u.id 
            WHERE p.receiver_id = %s AND p.status = 'pending_approval'
        """, (st.session_state.user['id'],))
        
        if not my_apps.empty:
            for _, a in my_apps.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"💰 {a['payer_name']} ödeme yaptı: **{a['amount']:.2f} ₺**")
                if c2.button("Onayla 👍", key=f"a_{a['id']}"):
                    run_query("UPDATE payments SET status = 'paid' WHERE id = %s", (int(a['id']),), is_select=False)
                    st.rerun()
        else: st.write("Onaylanacak ödeme yok.")
