import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Daire 6 Akıllı Panel", page_icon="🏠", layout="centered")

TR_AYLAR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}

# YENİ EV SAKİNLERİ
EV_SAKINLERI = ["Metin", "Zafer", "Murat", "Mehmet"]

if 'kesinti_siniri' not in st.session_state: st.session_state['kesinti_siniri'] = 300
if 'buy_item_id' not in st.session_state: st.session_state['buy_item_id'] = None

# --- GELİŞMİŞ CSS & ANİMASYON ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; } 
    .status-card { background: linear-gradient(145deg, #1e1e1e, #141414); padding: 1.5rem; border-radius: 15px; border-left: 5px solid #4CAF50; margin-bottom: 1rem; }
    .expense-card { background: linear-gradient(145deg, #161b22, #0d1117); padding: 1.5rem; border-radius: 15px; border-left: 5px solid #2196F3; margin-bottom: 1rem; }
    .announcement-box { background: linear-gradient(90deg, #ff8a00, #e52e71); padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 20px; color: white; box-shadow: 0 4px 15px rgba(229, 46, 113, 0.4); }
    .duty-box { background: #2a2e33; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #4CAF50; margin-bottom: 20px;}
    .list-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #222; }
    .text-green { color: #4CAF50; font-weight: bold; font-size: 1.1rem; }
    .text-blue { color: #2196F3; font-weight: bold; font-size: 1.1rem; }
    .text-muted { color: #888; font-size: 0.85rem; margin-top: 4px; }
    .buyer-badge { background:#2a2e33; padding:3px 8px; border-radius:12px; font-size:0.75rem; color:#bbb; margin-left:8px; }
    
    /* ENERJİ AKIŞ ANİMASYONU */
    @keyframes moveStripes {
        0% { background-position: 0 0; }
        100% { background-position: 40px 0; }
    }
    .energy-bar-fill {
        background-image: linear-gradient(45deg, rgba(255, 255, 255, 0.2) 25%, transparent 25%, transparent 50%, rgba(255, 255, 255, 0.2) 50%, rgba(255, 255, 255, 0.2) 75%, transparent 75%, transparent);
        background-size: 40px 40px;
        animation: moveStripes 1.5s linear infinite;
        border-radius: 20px;
    }
    </style>
""", unsafe_allow_html=True)

DB_URL = st.secrets["DATABASE_URL"]

# --- VERİTABANI İŞLEMLERİ ---
def execute_query(query, params=(), is_select=False):
    conn = psycopg2.connect(DB_URL)
    c = conn.cursor()
    c.execute(query, params)
    if is_select:
        cols = [desc[0] for desc in c.description]
        df = pd.DataFrame(c.fetchall(), columns=cols)
        conn.close()
        return df
    conn.commit()
    conn.close()

@st.cache_data(ttl=300)
def load_data(table, order_by="date_time DESC"):
    try: return execute_query(f"SELECT * FROM {table} ORDER BY {order_by}", is_select=True)
    except: return pd.DataFrame()

def clear_cache_all():
    load_data.clear()

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
            else: st.error("Hatalı giriş!")
    else:
        st.success("Yönetici girişi aktif.")
        if st.button("Çıkış Yap", use_container_width=True):
            st.session_state['admin_logged_in'] = False
            st.rerun()
            
        st.divider()
        st.subheader("📢 Ev Panosunu Güncelle")
        yeni_duyuru = st.text_area("Mesajınız:")
        if st.button("Panoya As", use_container_width=True):
            execute_query("UPDATE announcements SET message = %s, updated_at = CURRENT_TIMESTAMP WHERE id = (SELECT id FROM announcements LIMIT 1)", (yeni_duyuru,))
            clear_cache_all()
            st.success("Duyuru güncellendi!")
            st.rerun()

        st.divider()
        st.subheader("⚙️ Parametreler")
        yeni_sinir = st.number_input("Kesinti Sınırı (₺)", value=st.session_state['kesinti_siniri'], step=50)
        if st.button("Sınırı Güncelle", use_container_width=True):
            st.session_state['kesinti_siniri'] = yeni_sinir
            st.rerun()
            
        st.divider()
        st.subheader("🗑️ Veri Yönetimi")
        if st.button("Harcamaları Sıfırla", type="primary", use_container_width=True):
            execute_query("TRUNCATE TABLE expenses RESTART IDENTITY;")
            clear_cache_all()
            st.rerun()

# --- VERİLERİ YÜKLE ---
df_energy = load_data("readings", "date_time ASC")
df_exp = load_data("expenses")
df_shop = load_data("shopping_list", "date_added DESC")
try: df_ann = execute_query("SELECT message FROM announcements LIMIT 1", is_select=True)
except: df_ann = pd.DataFrame()

# ==========================================
# 📌 DUYURU VE NÖBET 
# ==========================================
if not df_ann.empty and df_ann.iloc[0]['message'].strip():
    st.markdown(f"<div class='announcement-box'>📌 {df_ann.iloc[0]['message']}</div>", unsafe_allow_html=True)

hafta_no = datetime.now().isocalendar()[1]
nobetci = EV_SAKINLERI[hafta_no % len(EV_SAKINLERI)]
st.markdown(f"<div class='duty-box'>🧹 <b>Bu Haftanın Temizlik ve Çöp Nöbetçisi:</b> <span style='color:#4CAF50; font-size:1.2rem;'>{nobetci}</span></div>", unsafe_allow_html=True)

# ==========================================
# ⚡ 1. BÖLÜM: ENERJİ YÖNETİMİ
# ==========================================
if not df_energy.empty:
    KESINTI_SINIRI = st.session_state['kesinti_siniri']
    latest = df_energy.iloc[-1]
    curr_bal, last_upd = latest['balance'], latest['date_time']
    percent = 100.0 if curr_bal >= 4000 else (0.0 if curr_bal <= KESINTI_SINIRI else ((curr_bal - KESINTI_SINIRI) / (4000 - KESINTI_SINIRI)) * 100)
    color = "#F44336" if percent < 15 else ("#FFC107" if percent < 40 else "#4CAF50")

    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_df = df_energy[df_energy['date_time'] >= seven_days_ago].copy()
    avg_daily = recent_df[recent_df['balance'].diff() < 0]['balance'].diff().abs().sum() / max(1, (recent_df['date_time'].max() - recent_df['date_time'].min()).days) if len(recent_df) > 1 else 0

    one_day_ago = last_upd - timedelta(hours=24.5)
    last_24h_df = df_energy[df_energy['date_time'] >= one_day_ago].copy()
    last_24h_cons = last_24h_df[last_24h_df['balance'].diff() < 0]['balance'].diff().abs().sum() if len(last_24h_df) > 1 else 0

    usable_bal = max(0, curr_bal - KESINTI_SINIRI)
    days_left = usable_bal / avg_daily if avg_daily > 0 else 0
    tahmini_kesinti_tarihi = datetime.now() + timedelta(days=days_left)

    st.markdown(f"""
        <div style="background:#1a1a1a; border-radius:15px; padding:20px; border:1px solid #333;">
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="color:#aaa;">⚡ KIBTEK Enerji Bakiye</span>
                <span style="font-weight:bold; color:{color};">%{percent:.1f}</span>
            </div>
            <div style="width:100%; height:25px; background:#333; border-radius:20px; overflow:hidden;">
                <div class="energy-bar-fill" style="width:{percent}%; height:100%; background-color:{color};"></div>
            </div>
            <div style="margin-top:15px; font-size:2rem; font-weight:bold;">{int(curr_bal)} ₺</div>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Son 24 Saat", f"{int(last_24h_cons)} ₺")
    with c2: st.metric("Günlük Ort.", f"{int(avg_daily)} ₺")
    with c3: st.metric("Kesinti Tahmini", f"{tahmini_kesinti_tarihi.day} {TR_AYLAR[tahmini_kesinti_tarihi.month]}")
st.write("---")

# ==========================================
# 🛒 2. BÖLÜM: İHTİYAÇ LİSTESİ (İNTERAKTİF)
# ==========================================
st.subheader("📝 Alınacaklar Listesi")
with st.form("shop_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1: s_item = st.text_input("Ne alınacak?", placeholder="Örn: Sıvı Sabun")
    with col2: s_adder = st.selectbox("Ekleyen", EV_SAKINLERI, key="shop_adder")
    with col3: 
        st.write("")
        s_submit = st.form_submit_button("Ekle", use_container_width=True)
    if s_submit and s_item:
        execute_query("INSERT INTO shopping_list (item_name, added_by) VALUES (%s, %s)", (s_item, s_adder))
        clear_cache_all()
        st.rerun()

if not df_shop.empty:
    for _, row in df_shop.iterrows():
        colA, colB = st.columns([4, 1])
        with colA: st.markdown(f"🛒 **{row['item_name']}** <span class='buyer-badge'>{row['added_by']}</span>", unsafe_allow_html=True)
        with colB:
            if st.button("Aldım ✅", key=f"buy_btn_{row['id']}", use_container_width=True):
                st.session_state['buy_item_id'] = row['id']
                st.rerun()
        
        # ALINAN ÜRÜNÜ HARCAMALARA AKTARMA KUTUSU
        if st.session_state['buy_item_id'] == row['id']:
            with st.container():
                st.markdown("<div style='background:#2a2e33; padding:15px; border-radius:10px; margin-bottom:15px;'>", unsafe_allow_html=True)
                st.write(f"💸 **{row['item_name']}** için harcama bilgisi:")
                b_price = st.number_input("Tutar (₺)", min_value=0.0, format="%.2f", step=10.0, key=f"price_{row['id']}")
                b_person = st.selectbox("Kim Ödedi?", EV_SAKINLERI, key=f"person_{row['id']}")
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button("Harcamalara Ekle", key=f"confirm_{row['id']}", type="primary", use_container_width=True):
                        if b_price > 0:
                            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            execute_query("INSERT INTO expenses (date_time, item_name, price, buyer) VALUES (%s, %s, %s, %s)", (now, row['item_name'], b_price, b_person))
                            execute_query("DELETE FROM shopping_list WHERE id = %s", (row['id'],))
                            st.session_state['buy_item_id'] = None
                            clear_cache_all()
                            st.rerun()
                        else: st.warning("Tutar girin!")
                with c_btn2:
                    if st.button("İptal", key=f"cancel_{row['id']}", use_container_width=True):
                        st.session_state['buy_item_id'] = None
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Buzdolabı dolu, eksik yok! 😎")

st.write("---")

# ==========================================
# 💰 3. BÖLÜM: HARCAMALAR VE HESAPLAŞMA
# ==========================================
st.subheader("💸 Ev Ekonomisi & Hesaplaşma")

with st.expander("➕ Harici Ev Harcaması Ekle"):
    with st.form("expense_form", clear_on_submit=True):
        e_item = st.text_input("Alınan Ürün / Hizmet")
        e_price = st.number_input("Tutar (₺)", min_value=0.0, format="%.2f", step=10.0)
        e_buyer = st.selectbox("Ödeyen Kişi", EV_SAKINLERI)
        if st.form_submit_button("Harcamalara Ekle"):
            if e_item and e_price > 0:
                execute_query("INSERT INTO expenses (date_time, item_name, price, buyer) VALUES (CURRENT_TIMESTAMP, %s, %s, %s)", (e_item, e_price, e_buyer))
                clear_cache_all()
                st.rerun()

total_expense = df_exp['price'].sum() if not df_exp.empty else 0
per_person = total_expense / len(EV_SAKINLERI)

st.markdown("#### ⚖️ Kimin Kime Borcu Var?")
if total_expense > 0:
    balances = {person: -per_person for person in EV_SAKINLERI}
    for buyer, amount in df_exp.groupby('buyer')['price'].sum().items():
        if buyer in balances: balances[buyer] += amount
        
    for person, bal in balances.items():
        if bal > 0.01: st.markdown(f"🟢 **{person}**: <span style='color:#4CAF50'>{bal:.2f} ₺ Alacaklı</span>", unsafe_allow_html=True)
        elif bal < -0.01: st.markdown(f"🔴 **{person}**: <span style='color:#F44336'>{abs(bal):.2f} ₺ Borçlu</span>", unsafe_allow_html=True)
        else: st.markdown(f"⚪ **{person}**: Ödeşildi", unsafe_allow_html=True)
else:
    st.info("Henüz harcama yok, herkesin cebi rahat.")

with st.expander("📋 Detaylı Harcama Dökümü"):
    if not df_exp.empty:
        for _, row in df_exp.head(10).iterrows(): 
            buyer_name = row.get('buyer', 'Bilinmiyor')
            st.markdown(f"<div class='list-item'><div><b>{row['item_name']}</b> <span class='buyer-badge'>👤 {buyer_name}</span></div><div class='text-blue'>{row['price']:,.2f} ₺</div></div>", unsafe_allow_html=True)

st.write("---")

# ==========================================
# 📈 4. BÖLÜM: ENERJİ GRAFİĞİ VE YÜKLEMELER
# ==========================================
st.subheader("📊 Enerji Grafiği ve Yüklemeler")

if not df_energy.empty:
    st.area_chart(df_energy.set_index('date_time')['balance'], height=200)
    
    df_energy['diff'] = df_energy['balance'].diff()
    recharges = df_energy[df_energy['diff'] > 20].copy().sort_values(by='date_time', ascending=False)
    
    st.markdown("#### ⚡ Son KIBTEK Yüklemeleri")
    if not recharges.empty:
        st.markdown('<div style="background:#161b22; border-radius:12px; padding:5px;">', unsafe_allow_html=True)
        for _, row in recharges.head(5).iterrows():
            st.markdown(f"""
                <div class="list-item">
                    <div>
                        <div style="font-weight:bold;">KIBTEK Yükleme</div>
                        <div class="text-muted">{row['date_time'].day} {TR_AYLAR[row['date_time'].month]} {row['date_time'].year}</div>
                    </div>
                    <div class="text-green">+{int(row['diff'])} ₺</div>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Henüz bir yükleme hareketi tespit edilmedi.")
