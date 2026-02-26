import os
import time
import psycopg2
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

# GÜVENLİK: Bağlantı adresini dışarıdan alıyoruz
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_balance():
    chrome_options = Options()
    chrome_options.add_argument("--headless") # GitHub Actions'da çalışması için headless ŞARTTIR
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
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
            # PostgreSQL'e Bağlan ve Kaydet
            conn = psycopg2.connect(DATABASE_URL)
            c = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            c.execute("INSERT INTO readings (date_time, account_no, balance) VALUES (%s, %s, %s)", 
                      (now, HESAP_NO, bakiye))
            
            conn.commit()
            c.close()
            conn.close()
            print(f"\n✅ İŞLEM BAŞARILI!\nKayıt Zamanı: {now}\nKaydedilen Tutar: {bakiye} TL")
        except Exception as e:
            print(f"Veritabanı kayıt hatası: {e}")
    else:
        print("\n❌ İŞLEM BAŞARISIZ.")

if __name__ == "__main__":
    main()