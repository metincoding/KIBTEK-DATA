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

# --- GELİŞMİŞ CSS & ANİMASYON ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .status-card { background: #1e1e1e; padding: 1.2rem; border-radius: 12px; border-left: 5px solid #4CAF50; margin-bottom: 1rem; }
    .list-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #222; background: #161b22; margin-bottom: 5px; border-radius: 8px; }
    .debt-badge { background: #f44336; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: bold; }
    
    @keyframes moveStripes { 0% { background-position: 0 0; } 100% { background-position: 40px 0; } }
    .energy-bar-fill {
        background-image: linear-gradient(45deg, rgba(255,255,255,0.15) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.15) 50%, rgba(255,255,255,0.15) 75%, transparent 75%, transparent);
        background-size: 40px 40px; animation: moveStripes 1s linear infinite; border-radius: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- VERİTABANI YARDIMCI FONKSİYONU ---
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
        if not is_select: conn.rollback()
        return None

# --- SIDEBAR: GİRİŞ ---
with st.sidebar:
    if st.session_state.user is None:
        st.subheader("🔑 Giriş Yap")
        u_name = st.text_input("İsim")
        u_pass = st.text_input("Şifre", type="password")
        if st.button("Giriş", use_container_width=True):
            user_check = run_query("SELECT * FROM users WHERE username = %s AND password = %s", (u_name, u_pass))
            if user_check is not None and not user_check.empty:
                st.session_state.user = user_check.iloc[0].to_dict()
                st.rerun()
            else: st.error("Hatalı İsim veya Şifre!")
    else:
        st.success(f"Hoş geldin, {st.session_state.user['username']}")
        if st.button("Çıkış Yap", use_container_width=True):
            st.session_state.user = None
            st.rerun()
        
        if st.session_state.user['role'] == 'admin':
            st.divider()
            if st.button("🔴 Verileri Sıfırla"):
                run_query("TRUNCATE payments, expenses RESTART IDENTITY CASCADE", is_select=False)
                st.rerun()

# --- VERİLERİ YÜKLE ---
df_energy = run_query("SELECT * FROM readings ORDER BY date_time ASC")
if df_energy is not None and not df_energy.empty:
    df_energy['balance'] = pd.to_numeric(df_energy['balance'], errors='coerce')
    df_energy['date_time'] = pd.to_datetime(df_energy['date_time'])

# ==========================================
# 📊 ANA SAYFA (INDEX - READ ONLY)
# ==========================================
st.title("⚡ Daire 6 Ortak Panel")

# 1. ENERJİ DURUMU
if df_energy is not None and not df_energy.empty:
    curr_bal = float(df_energy.iloc[-1]['balance'])
    percent = max(0.0, min(100.0, ((curr_bal - 300) / 3700) * 100))
    color = "#F44336" if percent < 15 else ("#FFC107" if percent < 40 else "#4CAF50")

    st.markdown(f"""
        <div style="background:#1a1a1a; border-radius:15px; padding:20px; border:1px solid #333;">
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="color:#aaa;">KIBTEK Enerji Bakiye</span>
                <span style="font-weight:bold; color:{color};">%{percent:.1f}</span>
            </div>
            <div style="width:100%; height:25px; background:#333; border-radius:20px; overflow:hidden;">
                <div class="energy-bar-fill" style="width:{percent}%; height:100%; background-color:{color};"></div>
            </div>
            <div style="margin-top:15px; font-size:2.2rem; font-weight:bold;">{int(curr_bal)} ₺</div>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# 2. BORÇ DURUMU VE DETAYLAR
st.subheader("⚖️ Güncel Borç Listesi")
all_debts = run_query("""
    SELECT p.*, u.username as payer_name, r.username as receiver_name, e.item_name, e.date_time as exp_date
    FROM payments p 
    JOIN users u ON p.payer_id = u.id 
    JOIN users r ON p.receiver_id = r.id 
    JOIN expenses e ON p.expense_id = e.id
    WHERE p.status = 'pending_payment'
""")

if all_debts is not None and not all_debts.empty:
    for _, row in all_debts.iterrows():
        st.markdown(f"""
            <div class='list-item'>
                <div>
                    <b>{row['payer_name']}</b> ➔ {row['receiver_name']}<br>
                    <small style='color:#888'>{row['item_name']} (Ekleme: {row['exp_date'].strftime('%d %b')})</small>
                </div>
                <div style='text-align:right'>
                    <span class='debt-badge'>ÖDEME BEKLENİYOR</span><br>
                    <b style='color:#f44336'>{row['amount']:.2f} ₺</b>
                </div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.success("Tüm ödemeler yapıldı, kimsenin borcu yok! 😇")

# ==========================================
# 🔐 YETKİLİ ALAN (GİRİŞ ŞART)
# ==========================================
if st.session_state.user:
    st.divider()
    st.subheader(f"🛠️ Kullanıcı Paneli: {st.session_state.user['username']}")
    tab1, tab2 = st.tabs(["➕ Harcama Ekle", "💸 Borçlarımı Öde"])

    with tab1:
        with st.form("add_exp", clear_on_submit=True):
            item_name = st.text_input("Ne alındı? (Örn: Mutfak Alışverişi)")
            total_price = st.number_input("Toplam Tutar (₺)", min_value=0.0)
            if st.form_submit_button("Kaydet ve 4'e Böl"):
                if item_name and total_price > 0:
                    # Tek bir işlemde harcama ve borçları ekle
                    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
                    cur = conn.cursor()
                    try:
                        cur.execute("INSERT INTO expenses (item_name, price, buyer, date_time) VALUES (%s, %s, %s, NOW()) RETURNING id", 
                                    (item_name, total_price, st.session_state.user['username']))
                        exp_id = cur.fetchone()[0]
                        share = total_price / 4
                        for name in EV_SAKINLERI:
                            if name != st.session_state.user['username']:
                                cur.execute("INSERT INTO payments (expense_id, payer_id, receiver_id, amount) VALUES (%s, (SELECT id FROM users WHERE username=%s), (SELECT id FROM users WHERE username=%s), %s)", 
                                            (exp_id, name, st.session_state.user['username'], share))
                        conn.commit()
                        st.success("Harcama eklendi, borçlar paylaştırıldı!")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Hata oluştu: {e}")
                    finally: conn.close()

    with tab2:
        my_debts = run_query("""
            SELECT p.id, p.amount, e.item_name, r.username as receiver_name 
            FROM payments p 
            JOIN expenses e ON p.expense_id = e.id 
            JOIN users r ON p.receiver_id = r.id 
            WHERE p.payer_id = %s AND p.status = 'pending_payment'
        """, (int(st.session_state.user['id']),))
        
        if my_debts is not None and not my_debts.empty:
            for _, d in my_debts.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.write(f"🛒 **{d['item_name']}**<br><small>{d['receiver_name']}'e ödenecek</small>", unsafe_allow_html=True)
                if col2.button(f"{int(d['amount'])} ₺ Ödedim ✅", key=f"pay_{d['id']}", use_container_width=True):
                    run_query("UPDATE payments SET status = 'paid' WHERE id = %s", (int(d['id']),), is_select=False)
                    st.success("Ödeme tamamlandı!")
                    st.rerun()
        else:
            st.info("Şu an ödemen gereken bir borç yok. 😎")

# ==========================================
# 📈 ENERJİ GRAFİĞİ (SAYFA SONU)
# ==========================================
st.write("---")
st.subheader("📊 Enerji Kullanım Grafiği")
if df_energy is not None and not df_energy.empty:
    st.area_chart(df_energy.set_index('date_time')['balance'], height=200)
