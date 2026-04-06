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
    
    # 🌟 KRİTİK DÜZELTME: Farkları en başta TÜM veritabanı için hesaplıyoruz!
    df_energy['diff'] = df_energy['balance'].diff()

# ==========================================
# ⚡ 1. BÖLÜM: ENERJİ DURUMU 
# ==========================================
st.title("🏠 Daire 6 Ortak Panel")

if df_energy is not None and not df_energy.empty:
    curr_bal = float(df_energy.iloc[-1]['balance'])
    last_upd = df_energy.iloc[-1]['date_time']
    percent = max(0.0, min(100.0, ((curr_bal - 300) / 3700) * 100))
    color = "#F44336" if percent < 15 else ("#FFC107" if percent < 40 else "#4CAF50")
    
    # Metrik Hesaplamaları (Artık çok daha isabetli)
    seven_days_ago = last_upd - timedelta(days=7)
    recent_df = df_energy[df_energy['date_time'] >= seven_days_ago]
    
    avg_daily = 0.0
    if len(recent_df) > 1:
        total_drop = float(recent_df[recent_df['diff'] < 0]['diff'].abs().sum())
        time_span_days = (recent_df['date_time'].max() - recent_df['date_time'].min()).total_seconds() / 86400.0
        if time_span_days > 0: avg_daily = total_drop / max(1.0, time_span_days)
        else: avg_daily = total_drop
    
    # 🌟 SON 24 SAAT DÜZELTİLDİ
    one_day_ago = last_upd - timedelta(hours=28) # Toleranslı pencere
    last_24h_df = df_energy[df_energy['date_time'] >= one_day_ago]
    last_24h_cons = float(last_24h_df[last_24h_df['diff'] < 0]['diff'].abs().sum()) if len(last_24h_df) > 0 else 0.0

    days_left = int(max(0, curr_bal - 300) / avg_daily) if avg_daily > 0 else 0
    kesinti_tarihi = datetime.now() + timedelta(days=days_left)

    st.markdown(f"""
        <div style="background:#1a1a1a; border-radius:15px; padding:20px; border:1px solid #333;">
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="color:#aaa;">Kalan Enerji Bakiye</span>
                <span style="font-weight:bold; color:{color};">%{percent:.1f}</span>
            </div>
            <div style="width:100%; height:25px; background:#333; border-radius:20px; overflow:hidden;">
                <div class="energy-bar-fill" style="width:{percent}%; height:100%; background-color:{color};"></div>
            </div>
            <div style="margin-top:15px; font-size:2.2rem; font-weight:bold;">{int(curr_bal)} ₺</div>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Son 24 Saat", f"{int(last_24h_cons)} ₺")
    with c2: st.metric("Günlük Ort.", f"{int(avg_daily)} ₺")
    with c3: st.metric("Kalan", f"{days_left} Gün")

st.divider()

# ==========================================
# ⚖️ 2. BÖLÜM: AKILLI MAHSUPLAŞMA VE BORÇ LİSTESİ
# ==========================================
st.subheader("⚖️ Güncel Borç / Mahsuplaşma Listesi")

payments = run_query("""
    SELECT p.*, u.username as payer, r.username as receiver, e.item_name, e.date_time as date
    FROM payments p JOIN users u ON p.payer_id = u.id JOIN users r ON p.receiver_id = r.id JOIN expenses e ON p.expense_id = e.id
    WHERE p.status = 'pending_payment'
""")

if not payments.empty:
    net_matrix = payments.groupby(['payer', 'receiver'])['amount'].sum().reset_index()
    
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

    st.markdown("#### 🟡 Otomatik Mahsuplaşma")
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
    my_name = st.session_state.user['username']
    my_id = int(st.session_state.user['id'])
    
    st.subheader(f"🛠️ Kullanıcı Paneli: {my_name}")
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
                        cur.execute("INSERT INTO expenses (item_name, price, buyer, date_time) VALUES (%s, %s, %s, NOW()) RETURNING id", (item, price, my_name))
                        exp_id = cur.fetchone()[0]
                        share = price / 4
                        for name in EV_SAKINLERI:
                            if name != my_name:
                                cur.execute("INSERT INTO payments (expense_id, payer_id, receiver_id, amount, status) VALUES (%s, (SELECT id FROM users WHERE username=%s), (SELECT id FROM users WHERE username=%s), %s, 'pending_payment')", (exp_id, name, my_name, share))
                        conn.commit()
                        st.success("İşlendi!")
                        st.rerun()
                    except: conn.rollback()
                    finally: conn.close()

    with t2:
        st.write("Başkalarına olan **NET** borçlarınız (Ödemeyi yaptıktan sonra karşı taraftan onaylamasını isteyin):")
        if not payments.empty:
            borclar = {}
            for name in EV_SAKINLERI:
                if name == my_name: continue
                they_owe_me = payments[(payments['payer'] == name) & (payments['receiver'] == my_name)]['amount'].sum()
                i_owe_them = payments[(payments['payer'] == my_name) & (payments['receiver'] == name)]['amount'].sum()
                net_debt = i_owe_them - they_owe_me
                if net_debt > 0: borclar[name] = net_debt
            
            if borclar:
                for name, net_amount in borclar.items():
                    st.markdown(f"<div class='list-item'><div>👤 <b>{name}</b> kişisine net borcunuz:</div><div><b style='color:#f44336'>{int(net_amount)} ₺</b></div></div>", unsafe_allow_html=True)
            else: st.info("Kimseye net borcunuz yok, rahatsınız!")
        else: st.info("Kimseye net borcunuz yok, rahatsınız!")

    with t3:
        st.write("Sana olan net borcunu ödeyenleri buradan onayla ve sil:")
        if not payments.empty:
            alacaklar = {}
            for name in EV_SAKINLERI:
                if name == my_name: continue
                they_owe_me = payments[(payments['payer'] == name) & (payments['receiver'] == my_name)]['amount'].sum()
                i_owe_them = payments[(payments['payer'] == my_name) & (payments['receiver'] == name)]['amount'].sum()
                net_credit = they_owe_me - i_owe_them
                if net_credit > 0: alacaklar[name] = net_credit
            
            if alacaklar:
                for name, net_amount in alacaklar.items():
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"💰 **{name}**, tüm mahsuplaşmalar düşüldükten sonra sana net **{int(net_amount)} ₺** borçlu.", unsafe_allow_html=True)
                    if col2.button("Tahsil Ettim ✅", key=f"coll_{name}"):
                        run_query("""
                            UPDATE payments SET status = 'paid' 
                            WHERE status = 'pending_payment' 
                            AND ((payer_id = (SELECT id FROM users WHERE username=%s) AND receiver_id = %s) 
                              OR (payer_id = %s AND receiver_id = (SELECT id FROM users WHERE username=%s)))
                        """, (name, my_id, my_id, name), is_select=False)
                        st.rerun()
            else: st.write("Kimseden net bir alacağın kalmamış.")
        else: st.write("Kimseden net bir alacağın kalmamış.")

# ==========================================
# 📈 4. BÖLÜM: ENERJİ GRAFİKLERİ 
# ==========================================
st.divider()
st.subheader("📊 Enerji Kullanım Grafikleri")

if df_energy is not None and not df_energy.empty:
    
    st.markdown("**⚡ KIBTEK Bakiye Akışı**")
    st.area_chart(df_energy.set_index('date_time')['balance'], height=200)
    
    st.markdown("**📉 Günlük Tüketim Trendi**")
    df_cons_chart = df_energy.copy()
    df_cons_chart['date_only'] = df_cons_chart['date_time'].dt.date
    
    daily_cons = df_cons_chart[df_cons_chart['diff'] < 0].groupby('date_only')['diff'].sum().abs().reset_index()
    
    if not daily_cons.empty:
        daily_cons.rename(columns={'date_only': 'Tarih', 'diff': 'Tüketim (₺)'}, inplace=True)
        st.line_chart(daily_cons.set_index('Tarih')['Tüketim (₺)'], height=200)
    else:
        st.info("Henüz günlük tüketim grafiği oluşturacak kadar veri birikmedi.")

# ==========================================
# 📜 5. BÖLÜM: SİSTEM LOGLARI 
# ==========================================
st.divider()
st.subheader("📜 Sistem Logları (Son Hareketler)")

log_events = []

df_all_expenses = run_query("SELECT item_name, price, buyer, date_time FROM expenses")
if df_all_expenses is not None and not df_all_expenses.empty:
    for _, row in df_all_expenses.iterrows():
        log_events.append({
            'date': pd.to_datetime(row['date_time']),
            'icon': '🛒',
            'title': f"Harcama: {row['item_name']} ({row['buyer']})",
            'amount': -float(row['price']),
            'color': '#ff4b4b' 
        })

if df_energy is not None and not df_energy.empty:
    recharges = df_energy[df_energy['diff'] > 20]
    for _, row in recharges.iterrows():
        log_events.append({
            'date': pd.to_datetime(row['date_time']),
            'icon': '⚡',
            'title': 'KIBTEK Yükleme',
            'amount': float(row['diff']),
            'color': '#2ecc71' 
        })
        
    df_energy['date_only'] = df_energy['date_time'].dt.date
    daily_drops = df_energy[df_energy['diff'] < 0].groupby('date_only')['diff'].sum()
    for date_val, drop_val in daily_drops.items():
        dt_val = pd.to_datetime(date_val) + pd.Timedelta(hours=23, minutes=59) 
        if abs(drop_val) > 0:
            log_events.append({
                'date': dt_val,
                'icon': '🔌',
                'title': 'Elektrik Günlük Tüketi',
                'amount': float(drop_val),
                'color': '#ff9800' 
            })

log_events.sort(key=lambda x: x['date'], reverse=True)

if log_events:
    st.markdown('<div style="background:#161b22; border-radius:12px; padding:10px;">', unsafe_allow_html=True)
    for ev in log_events[:20]:
        amt_str = f"+{ev['amount']:.2f} ₺" if ev['amount'] > 0 else f"{ev['amount']:.2f} ₺"
        date_str = f"{ev['date'].day} {TR_AYLAR[ev['date'].month]} {ev['date'].strftime('%H:%M')}"
        st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; padding:10px; border-bottom:1px solid #2a2e33;">
                <div>
                    <span style="font-size:1.2rem; margin-right:10px;">{ev['icon']}</span>
                    <span style="font-weight:bold; color:#ddd;">{ev['title']}</span><br>
                    <small style="color:#888; margin-left:35px;">{date_str}</small>
                </div>
                <div style="font-weight:bold; color:{ev['color']}; font-size:1.1rem;">
                    {amt_str}
                </div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Sistemde henüz kaydedilmiş bir hareket bulunmuyor.")
