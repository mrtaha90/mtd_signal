from binance.client import Client
import pandas as pd
import time
import threading
from queue import Queue
import requests

# ----------------------------------------------------
# 🔑 Binance API Anahtarları
api_key = "NyU3gxsMwan2SuNWSff6ti1GUNAe8uge0GiPUUTLHz88tAd3oojljdZxK8EBx5Jg"
api_secret = "pfR2FzYPYjwSulzCghMUiwyQRGJT615rMepX7tNbqbJGGrMcfZUAdjci2GE5ANet"
client = Client(api_key, api_secret)

# ----------------------------------------------------
# 💬 Telegram Ayarları
TELEGRAM_TOKEN = '7612629548:AAHf_4FvXMb6g9ARRj0PIMJzIvYqLfFMPYI'
CHAT_ID = '5283753258'

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram gönderim hatası: {e}")

# ----------------------------------------------------
# 📈 RSI Fonksiyonu
def RSI(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ----------------------------------------------------
# RSI Hesaplama (Futures Verisiyle!)
def get_rsi(symbol, interval='5m', limit=100):
    try:
        klines = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=[
            'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close time', 'Quote asset volume', 'Number of trades',
            'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
        ])
        df['Close'] = df['Close'].astype(float)
        rsi = RSI(df['Close']).iloc[-1]
        return round(rsi, 2)
    except:
        return None

# ----------------------------------------------------
# RSI Sinyalini Kontrol Et
def check_rsi_signal(symbol):
    tf_map = {
        "5minute": "5m",
        "15minute": "15m",
        "1hour": "1h",
        "4hour": "4h"
    }

    rsi_values = {}
    for label, tf in tf_map.items():
        rsi = get_rsi(symbol, interval=tf)
        if rsi is None:
            return
        rsi_values[label] = rsi

    rsi_avg = sum(rsi_values.values()) / len(rsi_values)

    # RSI Şartları
    if rsi_values["5minute"] > 90 and rsi_values["15minute"] > 90 and rsi_avg >= 85:
        try:
            price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        except:
            price = "N/A"

        print(f"\n💰 [Futures] Sinyal Geldi: {symbol}")
        print(f"[Futures] RSI 5m: {rsi_values['5minute']}")
        print(f"[Futures] RSI 15m: {rsi_values['15minute']}")
        print(f"[Futures] RSI Ortalama: {round(rsi_avg, 2)}")
        print("-" * 50)

        # Telegram'a mesaj gönder
        message = f"""
📢 *[Futures] RSI Aşırı Yüksek Sinyali!*
🔸 Coin: `{symbol}`
🔹 RSI 5m: {rsi_values['5minute']}
🔹 RSI 15m: {rsi_values['15minute']}
🔹 RSI 1h: {rsi_values['1hour']}
🔹 RSI 4h: {rsi_values['4hour']}
🔸 Ortalama RSI: {round(rsi_avg, 2)}
💰 Fiyat: {price}
"""
        send_telegram_message(message)

# ----------------------------------------------------
# ✅ USDT-PERPETUAL Coinleri Listele (Futures Market)
def get_usdt_perpetual_symbols():
    exchange_info = client.futures_exchange_info()
    usdt_p_symbols = []
    for s in exchange_info['symbols']:
        if s['contractType'] == 'PERPETUAL' and s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING':
            usdt_p_symbols.append(s['symbol'])
    return usdt_p_symbols

# ----------------------------------------------------
# Worker - Her Coin için Thread
def worker(q):
    while not q.empty():
        symbol = q.get()
        print(f"⏱️ [Futures] Taranıyor: {symbol}")
        check_rsi_signal(symbol)
        q.task_done()

# ----------------------------------------------------
# Paralel Tarama Başlat
def run_multithreaded_scan(thread_count=5):
    symbols = get_usdt_perpetual_symbols()
    print(f"\n✅ [Futures] Taranacak Coin Sayısı: {len(symbols)}")
    q = Queue()
    for symbol in symbols:
        q.put(symbol)

    threads = []
    for _ in range(thread_count):
        t = threading.Thread(target=worker, args=(q,))
        t.start()
        threads.append(t)

    q.join()
    for t in threads:
        t.join()

# ----------------------------------------------------
# 🔁 Sonsuz Döngü – 2 Dakikada Bir Tarama
send_telegram_message("✅ RSI Bot Başladı! [Futures USDT-P] Taraması Aktif.")
while True:
    print("\n🚀 [Futures] Yeni tarama başlatılıyor...\n")
    run_multithreaded_scan(thread_count=5)
    print("\n⏳ [Futures] 2 dakika bekleniyor...\n")
    time.sleep(120)
