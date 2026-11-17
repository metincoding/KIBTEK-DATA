import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Daire 6 // Enterprise",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

TR_AYLAR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
}

EV_SAKINLERI = ["Metin", "Zafer", "Arda", "Mehmet"]

AVATAR_RENKLERI = {
    "Metin": "linear-gradient(135deg, #3B82F6, #1D4ED8)",
    "Zafer": "linear-gradient(135deg, #10B981, #047857)",
    "Arda": "linear-gradient(135deg, #8B5CF6, #5B21B6)",
    "Mehmet": "linear-gradient(135deg, #F59E0B, #B45309)"
}

if 'user' not in st.session_state:
    st.session_state.user = None

# --- ENTERPRISE FINTECH CSS (MOBILE-FIRST) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

:root {
    --bg-main: #07090E;
    --bg-card: #111622;
    --bg-card-hover: #161D2C;
    --border-subtle: rgba(255, 255, 255, 0.07);
    --text-primary: #F8FAFC;
    --text-muted: #94A3B8;
    --accent-green: #10B981;
    --accent-amber: #F59E0B;
    --accent-red: #F43F5E;
    --accent-blue: #38BDF8;
}

.stApp {
    background-color: var(--bg-main);
    background-image: radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.07) 0%, transparent 60%);
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Mobil için üst boşluğu optimize et ve gereksiz barları gizle */
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 3rem !important;
    max-width: 680px !important;
}
header[data-testid="stHeader"] {
    background: transparent !important;
}
#MainMenu, footer {
    visibility: hidden;
}

/* ÜST DURUM BARI (APP BAR) */
.enterprise-topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: rgba(17, 22, 34, 0.8);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    margin-bottom: 18px;
}
.brand-box {
    display: flex;
    align-items: center;
    gap: 10px;
}
.brand-logo {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, #38BDF8, #2563EB);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 1.1rem;
    color: white;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}
.brand-title {
    font-weight: 700;
    font-size: 1.05rem;
    letter-spacing: -0.3px;
    color: #FFFFFF;
    line-height: 1.1;
}
.brand-subtitle {
    font-size: 0.7rem;
    color: var(--text-muted);
    font-weight: 500;
}
.live-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.25);
    color: #34D399;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
}
.pulse-dot {
    width: 7px;
    height: 7px;
    background-color: #10B981;
    border-radius: 50%;
    box-shadow: 0 0 8px #10B981;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0% { transform: scale(0.95); opacity: 0.8; }
    50% { transform: scale(1.15); opacity: 1; }
    100% { transform: scale(0.95); opacity: 0.8; }
}

/* TELEMETRİ HERO KARTI */
.hero-card {
    background: linear-gradient(180deg, #131B2E 0%, #0D1320 100%);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 20px;
    padding: 20px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
}
.hero-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
}
.hero-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-muted);
    font-weight: 600;
}
.hero-balance {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.5rem;
    font-weight: 700;
    letter-spacing: -1px;
    color: #FFFFFF;
    line-height: 1.1;
    margin-top: 4px;
}
.hero-badge {
    padding: 5px 12px;
    border-radius: 999px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    font-weight: 700;
}
.progress-track {
    width: 100%;
    height: 14px;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 999px;
    overflow: hidden;
    margin: 14px 0 8px 0;
    padding: 2px;
    border: 1px solid rgba(255, 255, 255, 0.05);
}
@keyframes moveStripes {
    0% { background-position: 0 0; }
    100% { background-position: 28px 0; }
}
.progress-fill {
    height: 100%;
    border-radius: 999px;
    background-image: linear-gradient(
        45deg,
        rgba(255, 255, 255, 0.18) 25%,
        transparent 25%,
        transparent 50%,
        rgba(255, 255, 255, 0.18) 50%,
        rgba(255, 255, 255, 0.18) 75%,
        transparent 75%,
        transparent
    );
    background-size: 28px 28px;
    animation: moveStripes 1.2s linear infinite;
    transition: width 0.6s ease;
}
.hero-subtext {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 16px;
}

/* MOBİL UYUMLU 3'LÜ KPI GRID */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    padding-top: 14px;
    border-top: 1px solid var(--border-subtle);
}
.kpi-box {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 10px 12px;
    text-align: center;
}
.kpi-title {
    font-size: 0.68rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
    margin-bottom: 4px;
}
.kpi-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.15rem;
    font-weight: 700;
    color: #F8FAFC;
}

/* BÖLÜM BAŞLIKLARI */
.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 22px 0 12px 0;
}
.section-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #F8FAFC;
    letter-spacing: -0.2px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-pill {
    font-size: 0.72rem;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.05);
    padding: 3px 9px;
    border-radius: 999px;
    font-weight: 500;
}

/* FINTECH İŞLEM & TAKAS KARTLARI */
.tx-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 13px 15px;
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 14px;
    margin-bottom: 8px;
    transition: all 0.15s ease;
}
.tx-card:hover {
    background: var(--bg-card-hover);
    border-color: rgba(255, 255, 255, 0.14);
}
.tx-left {
    display: flex;
    align-items: center;
    gap: 12px;
}
.avatar-circle {
    width: 38px;
    height: 38px;
    border-radius: 11px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.9rem;
    color: white;
    flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}
.tx-names {
    font-size: 0.92rem;
    font-weight: 600;
    color: #F1F5F9;
    display: flex;
    align-items: center;
    gap: 6px;
}
.tx-arrow {
    color: #64748B;
    font-size: 0.8rem;
}
.tx-meta {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 2px;
}
.tx-right {
    text-align: right;
}
.tx-amount {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.05rem;
    font-weight: 700;
    margin-top: 3px;
}

/* ROZETLER (PILL BADGES) */
.badge-pill {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.4px;
    text-transform: uppercase;
}
.badge-red {
    background: rgba(244, 63, 94, 0.15);
    color: #FB7185;
    border: 1px solid rgba(244, 63, 94, 0.3);
}
.badge-yellow {
    background: rgba(245, 158, 11, 0.15);
    color: #FBBF24;
    border: 1px solid rgba(245, 158, 11, 0.3);
}
.badge-green {
    background: rgba(16, 185, 129, 0.15);
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

/* TAKAS ÖZET BARI */
.summary-strip {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 14px;
}
.summary-mini {
    background: rgba(17, 22, 34, 0.6);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 10px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.summary-mini-label {
    font-size: 0.73rem;
    color: var(--text-muted);
    font-weight: 500;
}
.summary-mini-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.95rem;
    font-weight: 700;
}

/* TERMİNAL LOG KUTUSU */
.log-terminal {
    background: #0B0F17;
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    max-height: 440px;
    overflow-y: auto;
    padding: 6px 12px;
}
.log-terminal::-webkit-scrollbar {
    width: 6px;
}
.log-terminal::-webkit-scrollbar-track {
    background: #0B0F17;
}
.log-terminal::-webkit-scrollbar-thumb {
    background: #1E293B;
    border-radius: 3px;
}
.log-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 11px 6px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}
.log-row:last-child {
    border-bottom: none;
}
.log-icon-box {
    width: 34px;
    height: 34px;
    border-radius: 9px;
    background: rgba(255, 255, 255, 0.04);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    flex-shrink: 0;
}

div[data-testid="stTabs"] button {
    font-weight: 600 !important;
    font-size: 0.85rem !important;
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
    except Exception:
        return pd.DataFrame()

# --- SIDEBAR: GİRİŞ & YÖNETİM ---
with st.sidebar:
    st.markdown("### 🛡️ Daire 6 Yönetim")
    if st.session_state.user is None:
        u_name = st.text_input("Kullanıcı Adı", key="sb_user")
        u_pass = st.text_input("Şifre", type="password", key="sb_pass")
        if st.button("Giriş Yap", use_container_width=True, type="primary"):
            user_check = run_query("SELECT * FROM users WHERE username = %s AND password = %s", (u_name, u_pass))
            if user_check is not None and not user_check.empty:
                st.session_state.user = user_check.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")
    else:
        st.success(f"👤 Aktif: **{st.session_state.user['username']}**")
        if st.button("Güvenli Çıkış", use_container_width=True):
            st.session_state.user = None
            st.rerun()

        if st.session_state.user['role'] == 'admin':
            st.divider()
            st.caption("⚠️ Yönetici Tehlikeli Bölge")
            if st.button("🔴 Tüm Verileri Sıfırla", use_container_width=True):
                run_query("TRUNCATE payments, expenses RESTART IDENTITY CASCADE", is_select=False)
                st.rerun()

# --- VERİLERİ YÜKLE ---
df_energy = run_query("SELECT * FROM readings ORDER BY date_time ASC")
if df_energy is not None and not df_energy.empty:
    df_energy['balance'] = pd.to_numeric(df_energy['balance'], errors='coerce')
    df_energy['date_time'] = pd.to_datetime(df_energy['date_time'])
    df_energy['diff'] = df_energy['balance'].diff()

# --- ÜST APP BAR ---
son_senkron_str = "Veri Bekleniyor"
if df_energy is not None and not df_energy.empty:
    lu = df_energy.iloc[-1]['date_time']
    son_senkron_str = f"KIBTEK: {lu.day} {TR_AYLAR[lu.month]} {lu.strftime('%H:%M')}"

aktif_kullanici_etiket = f"👤 {st.session_state.user['username']}" if st.session_state.user else "🔒 Salt Okunur"

st.markdown(f"""
<div class="enterprise-topbar">
    <div class="brand-box">
        <div class="brand-logo">D6</div>
        <div>
            <div class="brand-title">Daire 6 Enterprise</div>
            <div class="brand-subtitle">{aktif_kullanici_etiket}</div>
        </div>
    </div>
    <div class="live-pill">
        <span class="pulse-dot"></span>
        <span>{son_senkron_str}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# ⚡ 1. BÖLÜM: ENERJİ TELEMETRİ KARTI
# ==========================================
if df_energy is not None and not df_energy.empty:
    curr_bal = float(df_energy.iloc[-1]['balance'])
    last_upd = df_energy.iloc[-1]['date_time']

    # 7000 TL Üst Sınır - 300 TL Alt Sınır (6700 TL Kullanılabilir Bant)
    percent = max(0.0, min(100.0, ((curr_bal - 300) / 6700) * 100))
    if percent < 15:
        color = "#F43F5E"
        badge_bg = "rgba(244, 63, 94, 0.15)"
        durum_metni = "KRİTİK SEVİYE"
    elif percent < 40:
        color = "#F59E0B"
        badge_bg = "rgba(245, 158, 11, 0.15)"
        durum_metni = "DENGELİ"
    else:
        color = "#10B981"
        badge_bg = "rgba(16, 185, 129, 0.15)"
        durum_metni = "OPTİMAL"

    # Son 24 Saat Tüketimi
    one_day_ago = last_upd - timedelta(hours=24)
    past_df = df_energy[df_energy['date_time'] <= one_day_ago]
    if not past_df.empty:
        past_balance = float(past_df.iloc[-1]['balance'])
        last_24h_cons = max(0.0, past_balance - curr_bal)
    else:
        last_24h_cons = 0.0

    # Son 7 Günlük Ortalama
    seven_days_ago = last_upd - timedelta(days=7)
    recent_df = df_energy[df_energy['date_time'] >= seven_days_ago]
    avg_daily = 0.0
    if len(recent_df) > 1:
        total_drop = float(recent_df[recent_df['diff'] < 0]['diff'].abs().sum())
        time_span_days = (recent_df['date_time'].max() - recent_df['date_time'].min()).total_seconds() / 86400.0
        if time_span_days > 0:
            avg_daily = total_drop / max(1.0, time_span_days)

    # Kalan Gün ve Tahmini Kesinti Tarihi
    usable_balance = max(0.0, curr_bal - 300)
    days_left = int(usable_balance / avg_daily) if avg_daily > 0 else 0
    tahmini_kesinti = datetime.now() + timedelta(days=days_left)
    kesinti_str = f"{tahmini_kesinti.day} {TR_AYLAR[tahmini_kesinti.month]}" if avg_daily > 0 else "Hesaplanıyor"

    st.markdown(f"""
<div class="hero-card">
    <div class="hero-header">
        <div>
            <div class="hero-label">⚡ KIBTEK Akıllı Sayaç Bakiyesi</div>
            <div class="hero-balance">{int(curr_bal):,} ₺</div>
        </div>
        <div class="hero-badge" style="background:{badge_bg}; color:{color}; border:1px solid {color}44;">
            %{percent:.1f} • {durum_metni}
        </div>
    </div>
    <div class="progress-track">
        <div class="progress-fill" style="width:{percent}%; background-color:{color}; box-shadow: 0 0 12px {color}88;"></div>
    </div>
    <div class="hero-subtext">
        <span>Alt Sınır: 300 ₺ • Kapasite: 7.000 ₺</span>
        <span>Tahmini Kesinti: <strong style="color:#E2E8F0;">{kesinti_str}</strong></span>
    </div>
    <div class="kpi-grid">
        <div class="kpi-box">
            <div class="kpi-title">Son 24 Saat</div>
            <div class="kpi-value" style="color:#38BDF8;">{int(last_24h_cons)} ₺</div>
        </div>
        <div class="kpi-box">
            <div class="kpi-title">Günlük Ort.</div>
            <div class="kpi-value" style="color:#FBBF24;">{int(avg_daily)} ₺</div>
        </div>
        <div class="kpi-box">
            <div class="kpi-title">Kalan Süre</div>
            <div class="kpi-value" style="color:{color};">{days_left} Gün</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 MOBİL HIZLI GİRİŞ & KULLANICI PANELİ
# ==========================================
payments = run_query("""
    SELECT p.*, u.username as payer, r.username as receiver, e.item_name, e.date_time as date
    FROM payments p
    JOIN users u ON p.payer_id = u.id
    JOIN users r ON p.receiver_id = r.id
    JOIN expenses e ON p.expense_id = e.id
    WHERE p.status = 'pending_payment'
""")

# 🌟 KRİTİK DÜZELTME: PostgreSQL Decimal tipini float'a çeviriyoruz
if payments is not None and not payments.empty:
    payments['amount'] = pd.to_numeric(payments['amount'], errors='coerce').fillna(0.0)
    payments['date'] = pd.to_datetime(payments['date'])

if st.session_state.user is None:
    with st.expander("🔑 Harcama Eklemek veya Tahsilat Onaylamak İçin Giriş Yapın"):
        col_u, col_p, col_b = st.columns([2, 2, 1])
        with col_u:
            m_user = st.selectbox("Ev Sakini Seçin", EV_SAKINLERI, label_visibility="collapsed")
        with col_p:
            m_pass = st.text_input("Şifre", type="password", placeholder="Şifreniz...", label_visibility="collapsed")
        with col_b:
            if st.button("Giriş", use_container_width=True, type="primary"):
                u_chk = run_query("SELECT * FROM users WHERE username = %s AND password = %s", (m_user, m_pass))
                if u_chk is not None and not u_chk.empty:
                    st.session_state.user = u_chk.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Hatalı şifre!")
else:
    my_name = st.session_state.user['username']
    my_id = int(st.session_state.user['id'])

    # Kullanıcının Kişisel Net Pozisyonunu Hesapla
    toplam_alacak = 0.0
    toplam_borc = 0.0
    if not payments.empty:
        for name in EV_SAKINLERI:
            if name == my_name:
                continue
            they_owe = float(payments[(payments['payer'] == name) & (payments['receiver'] == my_name)]['amount'].sum())
            i_owe = float(payments[(payments['payer'] == my_name) & (payments['receiver'] == name)]['amount'].sum())
            fark = they_owe - i_owe
            if fark > 0:
                toplam_alacak += fark
            elif fark < 0:
                toplam_borc += abs(fark)

    st.markdown(f"""
<div class="section-header">
    <div class="section-title">🛠️ Finansal Çalışma Alanı: {my_name}</div>
    <div class="section-pill">Net Alacak: +{int(toplam_alacak)} ₺ | Net Borç: -{int(toplam_borc)} ₺</div>
</div>
""", unsafe_allow_html=True)

    t1, t2, t3 = st.tabs([
        "➕ Yeni Harcama",
        f"💸 Net Borçlarım ({int(toplam_borc)} ₺)",
        f"🏦 Alacaklarım ({int(toplam_alacak)} ₺)"
    ])

    with t1:
        with st.form("new_exp", clear_on_submit=True):
            c_item, c_price = st.columns([2, 1])
            with c_item:
                item = st.text_input("Ne alındı?", placeholder="Örn: Damacana Su, Deterjan...")
            with c_price:
                price = st.number_input("Toplam Fiyat (₺)", min_value=0.0, step=10.0)
            if st.form_submit_button("Harcamayı Kaydet ve 4'e Böl", use_container_width=True, type="primary"):
                if item and price > 0:
                    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
                    cur = conn.cursor()
                    try:
                        cur.execute(
                            "INSERT INTO expenses (item_name, price, buyer, date_time) VALUES (%s, %s, %s, NOW()) RETURNING id",
                            (item, price, my_name)
                        )
                        exp_id = cur.fetchone()[0]
                        share = price / 4.0
                        for name in EV_SAKINLERI:
                            if name != my_name:
                                cur.execute(
                                    "INSERT INTO payments (expense_id, payer_id, receiver_id, amount, status) VALUES (%s, (SELECT id FROM users WHERE username=%s), (SELECT id FROM users WHERE username=%s), %s, 'pending_payment')",
                                    (exp_id, name, my_name, share)
                                )
                        conn.commit()
                        st.success(f"{item} eklendi! Kişi başı {int(share)} ₺ yansıtıldı.")
                        st.rerun()
                    except Exception:
                        conn.rollback()
                    finally:
                        conn.close()

    with t2:
        if not payments.empty:
            borclar = {}
            for name in EV_SAKINLERI:
                if name == my_name:
                    continue
                they_owe_me = float(payments[(payments['payer'] == name) & (payments['receiver'] == my_name)]['amount'].sum())
                i_owe_them = float(payments[(payments['payer'] == my_name) & (payments['receiver'] == name)]['amount'].sum())
                net_debt = i_owe_them - they_owe_me
                if net_debt > 0:
                    borclar[name] = net_debt

            if borclar:
                st.caption("Ödemeyi yaptıktan sonra ilgili kişiden kendi panelinde 'Tahsil Ettim' butonuna basmasını isteyin:")
                for name, net_amount in borclar.items():
                    av_bg = AVATAR_RENKLERI.get(name, "#475569")
                    st.markdown(f"""
<div class="tx-card">
    <div class="tx-left">
        <div class="avatar-circle" style="background:{av_bg};">{name[0]}</div>
        <div>
            <div class="tx-names">{my_name} <span class="tx-arrow">➔</span> {name}</div>
            <div class="tx-meta">Mahsuplaşma sonrası net borcunuz</div>
        </div>
    </div>
    <div class="tx-right">
        <span class="badge-pill badge-red">ÖDENECEK</span>
        <div class="tx-amount" style="color:#FB7185;">{int(net_amount)} ₺</div>
    </div>
</div>
""", unsafe_allow_html=True)
            else:
                st.success("Kimseye net borcunuz bulunmuyor!")
        else:
            st.success("Kimseye net borcunuz bulunmuyor!")

    with t3:
        if not payments.empty:
            alacaklar = {}
            for name in EV_SAKINLERI:
                if name == my_name:
                    continue
                they_owe_me = float(payments[(payments['payer'] == name) & (payments['receiver'] == my_name)]['amount'].sum())
                i_owe_them = float(payments[(payments['payer'] == my_name) & (payments['receiver'] == name)]['amount'].sum())
                net_credit = they_owe_me - i_owe_them
                if net_credit > 0:
                    alacaklar[name] = net_credit

            if alacaklar:
                st.caption("Ödemeyi teslim aldığınızda 'Tahsil Ettim' butonuna basarak aranızdaki tüm açık kayıtları kapatın:")
                for name, net_amount in alacaklar.items():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"💰 **{name}** size net **{int(net_amount)} ₺** borçlu.")
                    with col2:
                        if st.button("Tahsil Ettim ✅", key=f"coll_{name}", use_container_width=True, type="primary"):
                            run_query("""
                                UPDATE payments SET status = 'paid'
                                WHERE status = 'pending_payment'
                                AND ((payer_id = (SELECT id FROM users WHERE username=%s) AND receiver_id = %s)
                                  OR (payer_id = %s AND receiver_id = (SELECT id FROM users WHERE username=%s)))
                            """, (name, my_id, my_id, name), is_select=False)
                            st.rerun()
            else:
                st.info("Kimseden bekleyen net bir alacağınız yok.")
        else:
            st.info("Kimseden bekleyen net bir alacağınız yok.")

# ==========================================
# ⚖️ 2. BÖLÜM: AKILLI TAKAS & MAHSUPLAŞMA MERKEZİ
# ==========================================
st.markdown("""
<div class="section-header">
    <div class="section-title">⚖️ Akıllı Takas & Mahsuplaşma Merkezi</div>
    <div class="section-pill">Canlı Bilanço</div>
</div>
""", unsafe_allow_html=True)

if not payments.empty:
    net_matrix = payments.groupby(['payer', 'receiver'])['amount'].sum().reset_index()

    # Özet İstatistik Hesapla
    aktif_nakit_toplam = 0.0
    mahsup_toplam = 0.0
    net_transferler = []
    processed_pairs = set()

    for _, row in net_matrix.iterrows():
        p1, p2 = row['payer'], row['receiver']
        pair = tuple(sorted((p1, p2)))
        if pair in processed_pairs:
            continue
        processed_pairs.add(pair)

        amt1 = float(net_matrix[(net_matrix['payer'] == p1) & (net_matrix['receiver'] == p2)]['amount'].sum())
        amt2 = float(net_matrix[(net_matrix['payer'] == p2) & (net_matrix['receiver'] == p1)]['amount'].sum())

        mahsup_toplam += min(amt1, amt2)
        diff = amt1 - amt2
        if diff > 0:
            aktif_nakit_toplam += diff
            net_transferler.append((p1, p2, diff))
        elif diff < 0:
            aktif_nakit_toplam += abs(diff)
            net_transferler.append((p2, p1, abs(diff)))

    st.markdown(f"""
<div class="summary-strip">
    <div class="summary-mini">
        <span class="summary-mini-label">🔴 Bekleyen Net Nakit</span>
        <span class="summary-mini-val" style="color:#FB7185;">{int(aktif_nakit_toplam)} ₺</span>
    </div>
    <div class="summary-mini">
        <span class="summary-mini-label">🟡 Eritilen (Mahsup)</span>
        <span class="summary-mini-val" style="color:#FBBF24;">{int(mahsup_toplam)} ₺</span>
    </div>
</div>
""", unsafe_allow_html=True)

    # 1. NAKİT ÖDEME BEKLEYENLER
    if net_transferler:
        for borclu, alacakli, tutar in net_transferler:
            av_bg = AVATAR_RENKLERI.get(borclu, "#475569")
            st.markdown(f"""
<div class="tx-card">
    <div class="tx-left">
        <div class="avatar-circle" style="background:{av_bg};">{borclu[0]}</div>
        <div>
            <div class="tx-names">{borclu} <span class="tx-arrow">➔</span> {alacakli}</div>
            <div class="tx-meta">Mahsuplaşma sonrası net nakit transferi</div>
        </div>
    </div>
    <div class="tx-right">
        <span class="badge-pill badge-red">ÖDEME BEKLENİYOR</span>
        <div class="tx-amount" style="color:#FB7185;">{int(tutar)} ₺</div>
    </div>
</div>
""", unsafe_allow_html=True)

    # 2. OTOMATİK MAHSUPLAŞMA LİSTESİ
    offset_rows = []
    for _, row in payments.iterrows():
        opp_amt = float(net_matrix[(net_matrix['payer'] == row['receiver']) & (net_matrix['receiver'] == row['payer'])]['amount'].sum())
        if opp_amt > 0:
            offset_rows.append(row)

    if offset_rows:
        with st.expander(f"🟡 Otomatik Mahsuplaşan Harcama Detayları ({len(offset_rows)} İşlem)", expanded=True):
            for row in offset_rows:
                av_bg = AVATAR_RENKLERI.get(row['payer'], "#475569")
                tarih_str = f"{row['date'].day} {TR_AYLAR[row['date'].month]}"
                st.markdown(f"""
<div class="tx-card" style="opacity:0.82;">
    <div class="tx-left">
        <div class="avatar-circle" style="background:{av_bg}; width:32px; height:32px; font-size:0.8rem;">{row['payer'][0]}</div>
        <div>
            <div class="tx-names" style="font-size:0.86rem;">{row['payer']} <span class="tx-arrow">➔</span> {row['receiver']}</div>
            <div class="tx-meta">🛒 {row['item_name']} • {tarih_str}</div>
        </div>
    </div>
    <div class="tx-right">
        <span class="badge-pill badge-yellow">MAHSUPLAŞILDI</span>
        <div class="tx-amount" style="color:#FBBF24; font-size:0.95rem;">{int(row['amount'])} ₺</div>
    </div>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown("""
<div class="tx-card" style="justify-content:center; padding:20px; border-color:rgba(16,185,129,0.3);">
    <span style="color:#34D399; font-weight:600;">✨ Tüm hesaplar mutabık! Bekleyen borç veya alacak bulunmuyor.</span>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 📈 3. BÖLÜM: ENERJİ ANALİTİK GRAFİKLERİ
# ==========================================
st.markdown("""
<div class="section-header">
    <div class="section-title">📊 Enerji Telemetri & Tüketim Analitiği</div>
    <div class="section-pill">Canlı Grafikler</div>
</div>
""", unsafe_allow_html=True)

if df_energy is not None and not df_energy.empty:
    g_tab1, g_tab2 = st.tabs(["📉 Günlük Tüketim Trendi (₺)", "⚡ KIBTEK Bakiye Akışı (₺)"])

    with g_tab1:
        df_cons_chart = df_energy.copy()
        df_cons_chart['date_only'] = df_cons_chart['date_time'].dt.date
        daily_cons = df_cons_chart[df_cons_chart['diff'] < 0].groupby('date_only')['diff'].sum().abs().reset_index()

        if not daily_cons.empty:
            daily_cons.rename(columns={'date_only': 'Tarih', 'diff': 'Tüketim (₺)'}, inplace=True)
            st.line_chart(daily_cons.set_index('Tarih')['Tüketim (₺)'], height=220, color="#F59E0B")
        else:
            st.info("Henüz günlük tüketim grafiği oluşturacak kadar veri birikmedi.")

    with g_tab2:
        st.area_chart(df_energy.set_index('date_time')['balance'], height=220, color="#38BDF8")

# ==========================================
# 📜 4. BÖLÜM: DENETİM İZİ (SON 100 HAREKET)
# ==========================================
st.markdown("""
<div class="section-header">
    <div class="section-title">📜 Sistem Denetim Logları</div>
    <div class="section-pill">Son 100 Hareket</div>
</div>
""", unsafe_allow_html=True)

log_events = []

df_all_expenses = run_query("SELECT item_name, price, buyer, date_time FROM expenses")
if df_all_expenses is not None and not df_all_expenses.empty:
    df_all_expenses['price'] = pd.to_numeric(df_all_expenses['price'], errors='coerce').fillna(0.0)
    for _, row in df_all_expenses.iterrows():
        log_events.append({
            'date': pd.to_datetime(row['date_time']),
            'type': 'expense',
            'icon': '🛒',
            'title': f"{row['item_name']} ({row['buyer']})",
            'subtitle': 'Ev Ortak Harcaması',
            'amount': -float(row['price']),
            'color': '#FB7185'
        })

if df_energy is not None and not df_energy.empty:
    recharges = df_energy[df_energy['diff'] > 20]
    for _, row in recharges.iterrows():
        log_events.append({
            'date': pd.to_datetime(row['date_time']),
            'type': 'energy',
            'icon': '⚡',
            'title': 'KIBTEK Bakiye Yükleme',
            'subtitle': 'Sayaç Kredi Girişi',
            'amount': float(row['diff']),
            'color': '#34D399'
        })

    df_energy['date_only'] = df_energy['date_time'].dt.date
    daily_drops = df_energy[df_energy['diff'] < 0].groupby('date_only')['diff'].sum()
    for date_val, drop_val in daily_drops.items():
        dt_val = pd.to_datetime(date_val) + pd.Timedelta(hours=23, minutes=59)
        if abs(drop_val) > 0:
            log_events.append({
                'date': dt_val,
                'type': 'energy',
                'icon': '🔌',
                'title': 'Elektrik Günlük Tüketim',
                'subtitle': 'Otomatik Sayaç Düşümü',
                'amount': float(drop_val),
                'color': '#FBBF24'
            })

log_events.sort(key=lambda x: x['date'], reverse=True)

if log_events:
    f_tab1, f_tab2, f_tab3 = st.tabs(["📋 Tümü", "🛒 Ev Harcamaları", "⚡ Enerji Logları"])

    def render_logs(events_list):
        if not events_list:
            st.info("Bu kategoride kayıt bulunmuyor.")
            return
        rows_html = '<div class="log-terminal">'
        for ev in events_list[:100]:
            amt_str = f"+{ev['amount']:.2f} ₺" if ev['amount'] > 0 else f"{ev['amount']:.2f} ₺"
            date_str = f"{ev['date'].day} {TR_AYLAR[ev['date'].month]} • {ev['date'].strftime('%H:%M')}"
            rows_html += (
                f'<div class="log-row">'
                f'<div class="tx-left">'
                f'<div class="log-icon-box">{ev["icon"]}</div>'
                f'<div>'
                f'<div style="font-weight:600; font-size:0.88rem; color:#F1F5F9;">{ev["title"]}</div>'
                f'<div style="font-size:0.72rem; color:#64748B;">{ev["subtitle"]} • {date_str}</div>'
                f'</div>'
                f'</div>'
                f'<div style="font-family:\'JetBrains Mono\', monospace; font-weight:700; color:{ev["color"]}; font-size:0.95rem;">'
                f'{amt_str}'
                f'</div>'
                f'</div>'
            )
        rows_html += '</div>'
        st.markdown(rows_html, unsafe_allow_html=True)

    with f_tab1:
        render_logs(log_events)
    with f_tab2:
        render_logs([e for e in log_events if e['type'] == 'expense'])
    with f_tab3:
        render_logs([e for e in log_events if e['type'] == 'energy'])
else:
    st.info("Sistemde henüz kaydedilmiş bir hareket bulunmuyor.")
