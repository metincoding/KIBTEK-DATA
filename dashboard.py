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

# --- GELİŞMİŞ CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .status-card { background: #1e1e1e; padding: 1.2rem; border-radius: 12px; border-left: 5px solid #4CAF50; margin-bottom: 1rem; }
    .list-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #222; background: #161b22; margin-bottom: 5px; border-radius: 8px; }
    
    .status-badge { padding: 4px 10px; border-radius: 12px; font-size: 0.7rem; font-weight: bold; color: white; }
    .bg-red { background: #ff4b4b; }     
    .bg-yellow { background: #f1c40f; color: black; }  
    .bg-green { background: #2ecc71; }   

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
        return pd.DataFrame()

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
            else: st.error("Hatalı Giriş!")
    else:
        st.success(f"Oturum: {st.session_state.user['username']}")
        if st.button("Çıkış Yap", use_container_width=True):
            st.session_state.user = None
            st.rerun()
        
        if st.session_state.user['role'] == 'admin':
            st.divider()
            if st.button("🔴 Tüm Datayı Sıfırla"):
                run_query("TRUNCATE payments, expenses RESTART IDENTITY CASCADE", is_select=False)
                st.rerun()

# --- VERİLERİ YÜKLE ---
df_energy = run_query("SELECT * FROM readings ORDER BY date_time ASC")
if df_energy is not None and not df_energy.empty:
    df_energy['balance'] = pd.to_numeric(df_energy['balance'], errors='coerce')
    df_energy['date_time'] = pd.to_datetime(df_energy['date_time'])

# ==========================================
# ⚡ 1. BÖLÜM: ENERJİ DURUMU (METRİKLER GERİ GELDİ)
# ==========================================
st.title("🏠 Daire 6 Ortak Panel")

if df_energy is not None and not df_energy.empty:
    curr_bal = float(df_energy.iloc[-1]['balance'])
    last_upd = df_energy.iloc[-1]['date_time']
    percent = max(0.0, min(100.0, ((curr_bal - 300) / 3700) * 100))
    color = "#F44336" if percent < 15 else ("#FFC107" if percent < 40 else "#4CAF50")
    
    # Kalan Gün Tahmini & Ortalama
    recent_df = df_energy[df_energy['date_time'] >= (datetime.now() - timedelta(days=7))].copy()
    avg_daily = recent_df[recent_df['balance'].diff() < 0]['balance'].diff().abs().sum() / max(1, (recent_df['date_time'].max() - recent_df['date_time'].min()).days) if len(recent_df) > 1 else 1
    
    # Son 24 Saat Tüketimi
    one_day_ago = last_upd - timedelta(hours=24.5)
    last_24h_df = df_energy[df_energy['date_time'] >= one_day_ago].copy()
    last_24h_cons = float(last_24h_df[last_24h_df['balance'].diff() < 0]['balance'].diff().abs().sum()) if len(last_24h_df) > 1 else 0

    days_left = int(max(0, curr_bal - 300) / avg_daily)
    kesinti_tarihi = datetime.now() + timedelta(days=days_left)

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

    # ALT METRİKLER (İstediğin Gibi Geri Döndü)
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Son 24 Saat", f"{int(last_24h_cons)} ₺")
    with c2: st.metric("Günlük Ort.", f"{int(avg_daily)} ₺")
    with c3: st.metric("Kalan", f"{days_left} Gün")

st.divider()

# ==========================================
# ⚖️ 2. BÖLÜM: AKILLI MAHSUPLAŞMA VE BORÇ LİSTESİ
# ==========================================
st.subheader("⚖️ Güncel Borç / Mahsuplaşma Listesi")

# pending_payment durumundaki borçlar (Onay süreci kalktı)
payments = run_query("""
    SELECT p.*, u.username as payer, r.username as receiver, e.item_name, e.date_time as date
    FROM payments p JOIN users u ON p.payer_id = u.id JOIN users r ON p.receiver_id = r.id JOIN expenses e ON p.expense_id = e.id
    WHERE p.status = 'pending_payment'
""")

if not payments.empty:
    net_matrix = payments.groupby(['payer', 'receiver'])['amount'].sum().reset_index()
    
    # 🔴 NAKİT ÖDEME BEKLENİYOR (Gerçek Borçlar)
    st.markdown("#### 🔴 Nakit Ödeme Bekleyenler")
    processed_pairs = set()
    for _, row in net_matrix.iterrows():
        p1, p2 = row['payer'], row['receiver']
        pair = tuple(sorted((p1, p2)))
        if pair in processed_pairs: continue
        processed_pairs.add(pair)
        
        amt1 = net_matrix[(net_matrix['payer'] == p1) & (net_matrix['receiver'] == p2)]['amount'].sum()
        amt2 = net_matrix[(net_matrix['payer'] == p2) & (net_matrix['receiver'] == p1)]['amount'].sum()
        
        diff = amt1 - amt2
        if diff > 0:
            st.markdown(f"<div class='list-item'><div><b>{p1}</b> ➔ {p2}</div><div style='text-align:right'><span class='status-badge bg-red'>ÖDEME BEKLENİYOR</span><br><b>{int(diff)} ₺</b></div></div>", unsafe_allow_html=True)
        elif diff < 0:
            st.markdown(f"<div class='list-item'><div><b>{p2}</b> ➔ {p1}</div><div style='text-align:right'><span class='status-badge bg-red'>ÖDEME BEKLENİYOR</span><br><b>{int(abs(diff))} ₺</b></div></div>", unsafe_allow_html=True)

    # 🟡 MAHSUPLAŞILAN İŞLEMLER
    st.markdown("#### 🟡 Mahsuplaşan Harcamalar")
    for _, row in payments.iterrows():
        opp_amt = net_matrix[(net_matrix['payer'] == row['receiver']) & (net_matrix['receiver'] == row['payer'])]['amount'].sum()
        if opp_amt > 0:
            st.markdown(f"""
                <div class='list-item' style='opacity:0.7'>
                    <div><b>{row['payer']}</b> ➔ {row['receiver']}<br><small>{row['item_name']} ({row['date'].day} {TR_AYLAR[row['date'].month]})</small></div>
                    <div style='text-align:right'><span class='status-badge bg-yellow'>MAHSUPLAŞILDI</span><br><b>{int(row['amount'])} ₺</b></div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.success("Herkes ödeşmiş, bekleyen borç yok! ✨")

# ==========================================
# 🛠️ 3. BÖLÜM: KULLANICI İŞLEMLERİ
# ==========================================
if st.session_state.user:
    st.divider()
    st.subheader(f"🛠️ Kullanıcı Paneli: {st.session_state.user['username']}")
    t1, t2, t3 = st.tabs(["➕ Harcama", "💸 Borçlarım", "🏦 Alacaklarım"])

    with t1:
        with st.form("new_exp", clear_on_submit=True):
            item = st.text_input("Ne alındı?")
            price = st.number_input("Toplam Fiyat", min_value=0.0)
            if st.form_submit_button("Kaydet ve Böl"):
                if item and price > 0:
                    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
                    cur = conn.cursor()
                    try:
                        cur.execute("INSERT INTO expenses (item_name, price, buyer, date_time) VALUES (%s, %s, %s, NOW()) RETURNING id", (item, price, st.session_state.user['username']))
                        exp_id = cur.fetchone()[0]
                        share = price / 4
                        for name in EV_SAKINLERI:
                            if name != st.session_state.user['username']:
                                cur.execute("INSERT INTO payments (expense_id, payer_id, receiver_id, amount, status) VALUES (%s, (SELECT id FROM users WHERE username=%s), (SELECT id FROM users WHERE username=%s), %s, 'pending_payment')", (exp_id, name, st.session_state.user['username'], share))
                        conn.commit()
                        st.success("İşlendi!")
                        st.rerun()
                    except: conn.rollback()
                    finally: conn.close()

    with t2:
        # Kişi sadece borçlarını GÖRÜR, işlem yapamaz.
        st.write("Başkalarına ödemen gereken borçlar (Parayı verdikten sonra alacaklıdan onaylamasını iste):")
        my_debts = run_query("SELECT p.id, p.amount, r.username as receiver, e.item_name FROM payments p JOIN expenses e ON p.expense_id = e.id JOIN users r ON p.receiver_id = r.id WHERE p.payer_id = %s AND p.status = 'pending_payment'", (int(st.session_state.user['id']),))
        if not my_debts.empty:
            for _, d in my_debts.iterrows():
                st.markdown(f"<div class='list-item'><div>🛒 <b>{d['item_name']}</b><br><small>{d['receiver']}'e ödenecek</small></div><div><b>{int(d['amount'])} ₺</b></div></div>", unsafe_allow_html=True)
        else:
            st.info("Kimseye borcun yok, rahatsın!")

    with t3:
        # SADECE ALACAKLI BUTONA BASABİLİR
        st.write("Sana olan borçlarını ödeyenleri buradan onayla ve sil:")
        my_collects = run_query("SELECT p.id, p.amount, u.username as payer, e.item_name FROM payments p JOIN expenses e ON p.expense_id = e.id JOIN users u ON p.payer_id = u.id WHERE p.receiver_id = %s AND p.status = 'pending_payment'", (int(st.session_state.user['id']),))
        if not my_collects.empty:
            for _, c in my_collects.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.write(f"💰 **{c['payer']}**, sana **{int(c['amount'])} ₺** ödedi mi?<br><small>({c['item_name']})</small>", unsafe_allow_html=True)
                # Alacaklı "Tahsil Ettim" dediği an status = 'paid' olur ve listeden kalkar.
                if col2.button("Tahsil Ettim ✅", key=f"coll_{c['id']}"):
                    run_query("UPDATE payments SET status = 'paid' WHERE id = %s", (int(c['id']),), is_select=False)
                    st.rerun()
        else: st.write("Kimseden bekleyen bir alacağın yok.")

# ==========================================
# 📈 4. BÖLÜM: ENERJİ GRAFİĞİ
# ==========================================
st.divider()
st.subheader("📊 Enerji Kullanım Grafiği")
if df_energy is not None and not df_energy.empty:
    st.area_chart(df_energy.set_index('date_time')['balance'], height=250)
