import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta

# --- PROFESYONEL AYARLAR ---
st.set_page_config(page_title="Daire 6 Pro", page_icon="🏠", layout="wide")

# Veritabanı Bağlantısı (Yardımcı Fonksiyon)
def run_query(query, params=(), is_select=True):
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

# --- AUTH LOGIC ---
if 'user' not in st.session_state:
    st.session_state.user = None

# ==========================================
# 🔐 SIDEBAR: GİRİŞ VE YÖNETİM
# ==========================================
with st.sidebar:
    st.title("👤 Kullanıcı Girişi")
    if st.session_state.user is None:
        u_name = st.text_input("Kullanıcı Adı")
        u_pass = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap"):
            user_check = run_query("SELECT * FROM users WHERE username = %s AND password = %s", (u_name, u_pass))
            if not user_check.empty:
                st.session_state.user = user_check.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("Hatalı giriş!")
    else:
        st.success(f"Hoş geldin, {st.session_state.user['username']}!")
        if st.button("Çıkış Yap"):
            st.session_state.user = None
            st.rerun()
        
        # Admin Özel: Kullanıcı Yönetimi
        if st.session_state.user['role'] == 'admin':
            st.divider()
            st.subheader("🛠️ Sistem Yönetimi")
            if st.button("Tüm Datayı Resetle (Kritik)"):
                run_query("TRUNCATE payments, expenses RESTART IDENTITY CASCADE", is_select=False)
                st.rerun()

# ==========================================
# 📊 ANA SAYFA (INDEX) - HERKESE AÇIK (SALT OKUNUR)
# ==========================================
st.title("⚡ Daire 6 Ortak Yaşam Paneli")

# 1. Enerji Kartları (Mevcut mantık korunuyor)
# ... (KIBTEK Metrikleri Buraya Gelecek) ...

st.divider()

# 2. BORÇ MATRİSİ (KİMİN KİME NE KADAR BORCU VAR?)
st.subheader("⚖️ Genel Borç Durumu")
all_payments = run_query("SELECT p.*, u.username as payer_name FROM payments p JOIN users u ON p.payer_id = u.id WHERE p.status != 'paid'")

if not all_payments.empty:
    # Kim, kime, ne kadar borçlu özeti
    summary = all_payments.groupby(['payer_name', 'receiver_id'])['amount'].sum().reset_index()
    for _, row in summary.iterrows():
        receiver = run_query("SELECT username FROM users WHERE id = %s", (int(row['receiver_id']),)).iloc[0]['username']
        st.warning(f"🔴 **{row['payer_name']}**, {receiver}'e **{row['amount']:.2f} ₺** borçlu.")
else:
    st.success("🎉 Harika! Şu an kimsenin kimseye onaylanmamış borcu yok.")

# ==========================================
# 🔑 ÜYE ÖZEL ALANI (SADECE GİRİŞ YAPILINCA)
# ==========================================
if st.session_state.user:
    st.divider()
    tabs = st.tabs(["➕ Harcama Ekle", "💸 Borçlarım", "✅ Onay Bekleyenler"])
    
    # TAB 1: HARCAMA EKLEME
    with tabs[0]:
        with st.form("new_expense"):
            item = st.text_input("Ürün Adı")
            price = st.number_input("Toplam Tutar", min_value=0.0)
            if st.form_submit_button("Harcamayı Kaydet ve Böl"):
                # 1. Harcamayı kaydet
                res = run_query("INSERT INTO expenses (item_name, price, buyer, date_time) VALUES (%s, %s, %s, NOW()) RETURNING id", 
                                (item, price, st.session_state.user['username']), is_select=True)
                exp_id = int(res.iloc[0]['id'])
                
                # 2. Diğer kullanıcılar için borç oluştur (4 kişi varsayımı)
                other_users = run_query("SELECT id FROM users WHERE id != %s", (st.session_state.user['id'],))
                share = price / 4
                for _, u in other_users.iterrows():
                    run_query("INSERT INTO payments (expense_id, payer_id, receiver_id, amount) VALUES (%s, %s, %s, %s)", 
                              (exp_id, int(u['id']), st.session_state.user['id'], share), is_select=False)
                st.success("Harcama eklendi ve borçlar paylaştırıldı!")
                st.rerun()

    # TAB 2: BORÇLARIM (ÖDEME YAPMA)
    with tabs[1]:
        my_debts = run_query("""
            SELECT p.*, e.item_name, u.username as receiver_name 
            FROM payments p 
            JOIN expenses e ON p.expense_id = e.id 
            JOIN users u ON p.receiver_id = u.id
            WHERE p.payer_id = %s AND p.status = 'pending_payment'
        """, (st.session_state.user['id'],))
        
        for _, d in my_debts.iterrows():
            col1, col2 = st.columns([3, 1])
            col1.write(f"🛒 {d['item_name']} ({d['receiver_name']}'e) - **{d['amount']:.2f} ₺**")
            if col2.button("Ödedim Bildir", key=f"pay_{d['id']}"):
                run_query("UPDATE payments SET status = 'pending_approval' WHERE id = %s", (int(d['id']),), is_select=False)
                st.rerun()

    # TAB 3: ONAY BEKLEYENLER (ALACAKLI OLDUĞUM ÖDEMELER)
    with tabs[2]:
        my_approvals = run_query("""
            SELECT p.*, e.item_name, u.username as payer_name 
            FROM payments p 
            JOIN expenses e ON p.expense_id = e.id 
            JOIN users u ON p.payer_id = u.id
            WHERE p.receiver_id = %s AND p.status = 'pending_approval'
        """, (st.session_state.user['id'],))
        
        for _, a in my_approvals.iterrows():
            col1, col2 = st.columns([3, 1])
            col1.write(f"💰 {a['payer_name']} ödeme yaptığını bildirdi: **{a['amount']:.2f} ₺**")
            if col2.button("Ödemeyi Onayla", key=f"app_{a['id']}"):
                run_query("UPDATE payments SET status = 'paid' WHERE id = %s", (int(a['id']),), is_select=False)
                st.rerun()

else:
    st.info("💡 Harcama eklemek veya ödemelerinizi yönetmek için soldan giriş yapın.")
