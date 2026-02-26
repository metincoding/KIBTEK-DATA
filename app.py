import os
import time
import psycopg2
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- AYARLAR ---
HESAP_NO = "00470913"
URL = "https://online.kibtek.com/?lang=tr&t=prepaid"

# GÜVENLİK
DATABASE_URL = os.environ.get("DATABASE_URL")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

def send_alert_email(bakiye, percent):
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL]):
        print("Mail ayarları eksik olduğu için uyarı gönderilemedi.")
        return

    subject = f"⚠️ KIBTEK Düşük Bakiye Uyarısı (%{percent:.1f})"
    body = (
        f"Merhaba,\n\n"
        f"KIBTEK sayacınızdaki bakiye kritik seviyeye (%10 veya altı) ulaştı.\n\n"
        f"Güncel Bakiye: {bakiye} TL\n"
        f"Doluluk Oranı: %{percent:.1f}\n\n"
        f"Lütfen kesinti yaşamamak için en kısa sürede yükleme yapınız.\n"
        f"Enerji Yönetim Paneli Botu"
    )
    
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("📧 Düşük bakiye uyarı e-postası başarıyla gönderildi!")
    except Exception as e:
        print(f"E-posta gönderme hatası: {e}")

def get_balance():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"Driver başlatma hatası: {e}")
        return None
    
    try:
        print("1. Siteye gidiliyor...")
        driver.get(URL)
        wait = WebDriverWait(driver, 20)

        input_selector = "#__next > div > main > div > div:nth-child(5) > form > div > div > input"
        input_box = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, input_selector)))
        input_box.clear()
        input_box.send_keys(HESAP_NO)
        time.sleep(1)

        btn_selector = "#__next > div > main > div > div:nth-child(5) > form > div > button"
        devam_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, btn_selector)))
        devam_btn.click()
        
        print("4. Sonuç sayfası bekleniyor...")
        balance_selector = "#__next > div > main > div > div:nth-child(5) > form > div:nth-child(5) > div:nth-child(1) > p"
        
        balance_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, balance_selector)))
        full_text = balance_element.text
    
        balance_str = ''.join(filter(lambda x: x.isdigit() or x == '.', full_text))
        balance_str = balance_str.strip('.')
        
        if balance_str:
            balance = int(float(balance_str)) 
            return balance
        else:
            print("Sayısal veri ayrıştırılamadı!")
            return None

    except Exception as e:
        print(f"HATA OLUŞTU: {e}")
        return None
    finally:
        driver.quit()

def main():
    print("Program Başlıyor...")
    
    if not DATABASE_URL:
        print("HATA: DATABASE_URL bulunamadı!")
        return

    bakiye = get_balance()
    
    if bakiye is not None:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            c = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            c.execute("INSERT INTO readings (date_time, account_no, balance) VALUES (%s, %s, %s)", 
                      (now, HESAP_NO, bakiye))
            conn.commit()
            c.close()
            conn.close()
            print(f"\n✅ İŞLEM BAŞARILI!\nKayıt Zamanı: {now}\nKaydedilen Tutar: {bakiye} TL")
            
            # --- YÜZDE HESAPLAMA VE MAİL KONTROLÜ ---
            if bakiye >= 4000:
                percent = 100.0
            elif bakiye <= 500:
                percent = (bakiye / 500) * 5.0
            else:
                percent = 5 + ((bakiye - 500) / 3500) * 95
                
            if percent <= 100.0:
                print("Bakiye %10 veya altına düştü! Uyarı maili tetikleniyor...")
                send_alert_email(bakiye, percent)
                
        except Exception as e:
            print(f"Veritabanı kayıt hatası: {e}")
    else:
        print("\n❌ İŞLEM BAŞARISIZ.")

if __name__ == "__main__":
    main()

