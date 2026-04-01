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
    
    /* DURUM ROZETLERİ */
    .status-badge { padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; color: black; }
    .bg-red { background: #ff4b4b; }     /* ÖDEME BEKLENİYOR */
    .bg-yellow { background: #ffea00; }  /* MAHSUPLAŞILDI */
    .bg-green { background: #2ecc71; }   /* ÖDENDİ */

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
            else: st.error("Hatalı Giriş!")
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
# 📊 ANA SAYFA (INDEX)
# ==========================================
st.title("⚡ Daire 6 Ortak Panel")

# 1. ENERJİ DURUMU (HATA DÜZELTMELİ)
if df_energy is not None and not df_energy.empty:
    curr_bal = float(df_energy.iloc[-1]['balance'])
    percent = max(0.0, min(100.0, ((curr_bal - 300) / 3700) * 100))
    color = "#F44336" if percent < 15 else ("#FFC107" if percent < 40 else "#4CAF50")
    
    # Kalan Gün Tahmini
    recent_df = df_energy[df_energy['date_time'] >= (datetime.now() - timedelta(days=7))].copy()
    avg_daily = recent_df[recent_df['balance'].diff() < 0]['balance'].diff().abs().sum() / max(1, (recent_df['date_time'].max() - recent_df['date_time'].min()).days) if len(recent_df) > 1 else 0
    days_left = int(max(0, curr_bal - 300) / avg_daily) if avg_daily > 0 else 0
    tahmini_tarih = datetime.now() + timedelta(days=days_left)

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
            <div style="color:#888; font-size:0.8rem; margin-top:5px;">Tahmini Kesinti: {tahmini_tarih.day} {TR_AYLAR[tahmini_tarih.month]} ({days_left} Gün)</div>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# ==========================================
# ⚖️ AKILLI MAHSUPLAŞMA MANTIĞI
# ==========================================
st.subheader("⚖️ Akıllı Hesaplaşma ve Net Borçlar")

# Tüm ödenmemiş borçları çek
all_pending = run_query("""
    SELECT p.*, u.username as payer_name, r.username as receiver_name, e.item_name
    FROM payments p 
    JOIN users u ON p.payer_id = u.id 
    JOIN users r ON p.receiver_id = r.id 
    JOIN expenses e ON p.expense_id = e.id
    WHERE p.status = 'pending_payment'
""")

if all_pending is not None and not all_pending.empty:
    # 1. Matris Oluştur: Kimin kime ne kadar toplam borcu var?
    matrix = all_pending.groupby(['payer_name', 'receiver_name'])['amount'].sum().reset_index()
    
    # 2. Mahsuplaşma Kartını Göster
    processed_pairs = set()
    st.markdown("#### 🔄 Karşılıklı Ödeşme Durumu")
    
    for _, row in matrix.iterrows():
        p1, p2 = row['payer_name'], row['receiver_name']
        pair = tuple(sorted((p1, p2)))
        if pair in processed_pairs: continue
        processed_pairs.add(pair)
        
        # Karşılıklı tutarları bul
        p1_to_p2 = matrix[(matrix['payer_name'] == p1) & (matrix['receiver_name'] == p2)]['amount'].sum()
        p2_to_p1 = matrix[(matrix['payer_name'] == p2) & (matrix['receiver_name'] == p1)]['amount'].sum()
        
        mahsuplasildi = min(p1_to_p2, p2_to_p1)
        
        if mahsuplasildi > 0:
            st.markdown(f"""
                <div class='list-item'>
                    <div>🤝 <b>{p1} & {p2}</b></div>
                    <div style='text-align:right'>
                        <span class='status-badge bg-yellow'>MAHSUPLAŞILDI</span><br>
                        <small style='color:#2ecc71'>-{int(mahsuplasildi)} ₺ mahsup edildi</small>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Net durumu yazdır
            diff = p1_to_p2 - p2_to_p1
            if diff > 0: st.caption(f"👉 Kalan: **{p1}**, {p2}'ye **{int(diff)} ₺** ödeyecek.")
            elif diff < 0: st.caption(f"👉 Kalan: **{p2}**, {p1}'ye **{int(abs(diff))} ₺** ödeyecek.")
            else: st.caption("👉 Durum: **Tamamen Ödeşildi!**")

    st.divider()
    
    # 3. Detaylı Hareket Listesi (3 Renk Durumu)
    st.markdown("#### 📜 Harcama Detayları")
    for _, row in all_pending.iterrows():
        # Bu harcama mahsuplaşmaya dahil mi? (Basit gösterim için)
        is_offset = False
        # Karşı taraftan bu kişiye borç var mı bakıyoruz
        opp_debt = matrix[(matrix['payer_name'] == row['receiver_name']) & (matrix['receiver_name'] == row['payer_name'])]['amount'].sum()
        
        badge_class = "bg-yellow" if opp_debt > 0 else "bg-red"
        status_text = "MAHSUPLAŞILDI" if opp_debt > 0 else "ÖDEME BEKLENİYOR"
        
        st.markdown(f"""
            <div class='list-item'>
                <div>
                    <b>{row['payer_name']}</b> ➔ {row['receiver_name']}<br>
                    <small style='color:#888'>{row['item_name']}</small>
                </div>
                <div style='text-align:right'>
                    <span class='status-badge {badge_class}'>{status_text}</span><br>
                    <b>{int(row['amount'])} ₺</b>
                </div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.success("Tüm ödemeler tamamlanmış! 😇")

# ==========================================
# 🔐 YETKİLİ ALAN (GİRİŞ ŞART)
# ==========================================
if st.session_state.user:
    st.divider()
    st.subheader(f"🛠️ Kullanıcı Paneli: {st.session_state.user['username']}")
    tab1, tab2 = st.tabs(["➕ Harcama Ekle", "💸 Borçlarımı Öde"])

    with tab1:
        with st.form("add_exp", clear_on_submit=True):
            item_name = st.text_input("Ürün/Hizmet")
            total_price = st.number_input("Tutar (₺)", min_value=0.0)
            if st.form_submit_button("Harcamayı Böl"):
                if item_name and total_price > 0:
                    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
                    cur = conn.cursor()
                    try:
                        cur.execute("INSERT INTO expenses (item_name, price, buyer, date_time) VALUES (%s, %s, %s, NOW()) RETURNING id", (item_name, total_price, st.session_state.user['username']))
                        exp_id = cur.fetchone()[0]
                        share = total_price / 4
                        for name in EV_SAKINLERI:
                            if name != st.session_state.user['username']:
                                cur.execute("INSERT INTO payments (expense_id, payer_id, receiver_id, amount) VALUES (%s, (SELECT id FROM users WHERE username=%s), (SELECT id FROM users WHERE username=%s), %s)", (exp_id, name, st.session_state.user['username'], share))
                        conn.commit()
                        st.success("İşlendi!")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Hata: {e}")
                    finally: conn.close()

    with tab2:
        # Ödenen kısımların yeşil görünmesi için status 'paid' yapılır
        my_debts = run_query("""
            SELECT p.id, p.amount, e.item_name, r.username as receiver_name 
            FROM payments p JOIN expenses e ON p.expense_id = e.id JOIN users r ON p.receiver_id = r.id 
            WHERE p.payer_id = %s AND p.status = 'pending_payment'
        """, (int(st.session_state.user['id']),))
        
        if my_debts is not None and not my_debts.empty:
            for _, d in my_debts.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.write(f"🛒 **{d['item_name']}** ({d['receiver_name']})")
                if col2.button(f"{int(d['amount'])} ₺ Ödedim", key=f"p_{d['id']}"):
                    run_query("UPDATE payments SET status = 'paid' WHERE id = %s", (int(d['id']),), is_select=False)
                    st.rerun()

# ==========================================
# 📈 ENERJİ GRAFİĞİ (DÜZELTİLDİ)
# ==========================================
st.write("---")
st.subheader("📊 Enerji Grafiği ve Yüklemeler")
if df_energy is not None and not df_energy.empty:
    st.area_chart(df_energy.set_index('date_time')['balance'], height=200)
    
    # Yüklemeler
    df_energy['diff'] = df_energy['balance'].diff()
    recharges = df_energy[df_energy['diff'] > 20].copy().sort_values(by='date_time', ascending=False)
    if not recharges.empty:
        for _, row in recharges.head(3).iterrows():
            st.markdown(f"<span style='color:#2ecc71'>✅ **{row['date_time'].day} {TR_AYLAR[row['date_time'].month]}**: +{int(row['diff'])} ₺ Yükleme (ÖDENDİ)</span>", unsafe_allow_html=True)
