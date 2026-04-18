import time
import os
import requests
from binance.client import Client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = Client(
    api_key=os.getenv("TESTNET_API_KEY"),
    api_secret=os.getenv("TESTNET_SECRET"),
    testnet=True
)

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def telegram_gonder(mesaj):
    try:
        token   = str(TELEGRAM_TOKEN).strip()
        chat_id = str(TELEGRAM_CHAT_ID).strip()
        url     = "https://api.telegram.org/bot" + token + "/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": mesaj}, timeout=10)
    except Exception as e:
        print(f"Telegram hata: {e}")

def hesapla_rsi(fiyatlar, periyot=14):
    kazanc, kayip = [], []
    for i in range(1, len(fiyatlar)):
        fark = fiyatlar[i] - fiyatlar[i-1]
        kazanc.append(max(fark, 0))
        kayip.append(abs(min(fark, 0)))
    ort_k = sum(kazanc[-periyot:]) / periyot
    ort_z = sum(kayip[-periyot:]) / periyot
    if ort_z == 0:
        return 100
    return 100 - (100 / (1 + ort_k / ort_z))

def hesapla_ema(fiyatlar, periyot):
    if len(fiyatlar) < periyot:
        return fiyatlar[-1]
    k   = 2 / (periyot + 1)
    ema = sum(fiyatlar[:periyot]) / periyot
    for f in fiyatlar[periyot:]:
        ema = f * k + ema * (1 - k)
    return ema

def hesapla_hacim_ort(hacimler, periyot=20):
    return sum(hacimler[-periyot:]) / periyot

def veri_al(sembol="BTCUSDT", interval="4h", limit=100):
    mumlar = client.get_klines(symbol=sembol, interval=interval, limit=limit)
    fiyatlar, hacimler = [], []
    for m in mumlar:
        fiyatlar.append(float(m[4]))
  
import time
import os
import requests
from binance.client import Client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = Client(
    api_key=os.getenv("TESTNET_API_KEY"),
    api_secret=os.getenv("TESTNET_SECRET"),
    testnet=True
)

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def telegram_gonder(mesaj):
    try:
        token   = str(TELEGRAM_TOKEN).strip()
        chat_id = str(TELEGRAM_CHAT_ID).strip()
        url     = "https://api.telegram.org/bot" + token + "/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": mesaj}, timeout=10)
    except Exception as e:
        print(f"Telegram hata: {e}")

def hesapla_rsi(fiyatlar, periyot=14):
    kazanc, kayip = [], []
    for i in range(1, len(fiyatlar)):
        fark = fiyatlar[i] - fiyatlar[i-1]
        kazanc.append(max(fark, 0))
        kayip.append(abs(min(fark, 0)))
    ort_k = sum(kazanc[-periyot:]) / periyot
    ort_z = sum(kayip[-periyot:]) / periyot
    if ort_z == 0:
        return 100
    return 100 - (100 / (1 + ort_k / ort_z))

def hesapla_ema(fiyatlar, periyot):
    if len(fiyatlar) < periyot:
        return fiyatlar[-1]
    k   = 2 / (periyot + 1)
    ema = sum(fiyatlar[:periyot]) / periyot
    for f in fiyatlar[periyot:]:
        ema = f * k + ema * (1 - k)
    return ema

def hesapla_hacim_ort(hacimler, periyot=20):
    return sum(hacimler[-periyot:]) / periyot

def veri_al(sembol="BTCUSDT", interval="4h", limit=100):
    mumlar = client.get_klines(symbol=sembol, interval=interval, limit=limit)
    fiyatlar, hacimler = [], []
    for m in mumlar:
        fiyatlar.append(float(m[4]))
        hacimler.append(float(m[5]))
    return fiyatlar, hacimler

def bakiye_al(varlik="USDT"):
    try:
        hesap = client.get_account()
        for v in hesap['balances']:
            if v['asset'] == varlik:
                return float(v['free'])
    except Exception as e:
        print(f"Bakiye hata: {e}")
    return 0.0

def sinyal_uret(fiyatlar, hacimler):
    if len(fiyatlar) < 70:
        return "BEKLE", 0, 0
    rsi       = hesapla_rsi(fiyatlar)
    ema50     = hesapla_ema(fiyatlar, 50)
    hacim_ort = hesapla_hacim_ort(hacimler)
    guncel    = fiyatlar[-1]
    gun_hacim = hacimler[-1]
    al = (rsi < 55 and guncel > ema50 and gun_hacim > hacim_ort * 1.1)
    return ("AL" if al else "BEKLE"), rsi, ema50

def bot_calistir():
    sembol       = "BTCUSDT"
    pozisyon_var = False
    giris_fiyati = 0.0
    islem_no     = 0

    basla_mesaji = (
        "🤖 Bot başladı — Testnet modu\n"
        "━━━━━━━━━━━━━━━━\n"
        "Strateji: RSI + EMA50 + Hacim\n"
        "AL sinyali : RSI < 55\n"
        "SAT sinyali: RSI > 60 veya\n"
        "             %5 kar / %2.5 stop-loss\n"
        "Kontrol    : Her 4 saatte bir\n"
        "━━━━━━━━━━━━━━━━"
    )
    print(basla_mesaji)
    telegram_gonder(basla_mesaji)

    while True:
        try:
            zaman              = datetime.now().strftime("%H:%M")
            fiyatlar, hacimler = veri_al(sembol, interval="4h", limit=100)
            guncel_fiyat       = fiyatlar[-1]
            rsi                = hesapla_rsi(fiyatlar)
            ema50              = hesapla_ema(fiyatlar, 50)
            usdt_bakiye        = bakiye_al("USDT")
            btc_bakiye         = bakiye_al("BTC")

            print(
                f"[{zaman}] BTC: ${guncel_fiyat:,.0f} | "
                f"RSI: {rsi:.1f} | EMA50: ${ema50:,.0f} | "
                f"USDT: ${usdt_bakiye:.1f} | "
                f"Poz: {'VAR' if pozisyon_var else 'YOK'}"
            )

            if pozisyon_var:
                kar_yuzde = (guncel_fiyat - giris_fiyati) / giris_fiyati
                cikis = None
                if kar_yuzde >= 0.05:
                    cikis = f"🎯 Kar al (+{kar_yuzde*100:.1f}%)"
                elif kar_yuzde <= -0.025:
                    cikis = f"🛑 Stop-loss ({kar_yuzde*100:.1f}%)"
                elif rsi > 60:
                    cikis = f"📉 RSI yüksek ({rsi:.1f})"

                if cikis:
                    btc_miktar = round(btc_bakiye * 0.99, 5)
                    if btc_miktar > 0:
                        client.order_market_sell(symbol=sembol, quantity=btc_miktar)
                        kar_usdt     = btc_miktar * (guncel_fiyat - giris_fiyati)
                        pozisyon_var = False
                        mesaj = (
                            f"{'✅' if kar_yuzde > 0 else '❌'} SATIŞ #{islem_no}\n"
                            f"━━━━━━━━━━━━━━━━\n"
                            f"Sebep  : {cikis}\n"
                            f"Fiyat  : ${guncel_fiyat:,.0f}\n"
                            f"Giriş  : ${giris_fiyati:,.0f}\n"
                            f"K/Z    : ${kar_usdt:+.2f}\n"
                            f"Bakiye : ${usdt_bakiye:,.1f}\n"
                            f"━━━━━━━━━━━━━━━━"
                        )
                        print(mesaj)
                        telegram_gonder(mesaj)
            else:
                sinyal, rsi_val, ema_val = sinyal_uret(fiyatlar, hacimler)
                if sinyal == "AL" and usdt_bakiye > 10:
                    harcama    = usdt_bakiye * 0.10
                    btc_miktar = round(harcama / guncel_fiyat, 5)
                    client.order_market_buy(symbol=sembol, quantity=btc_miktar)
                    pozisyon_var = True
                    giris_fiyati = guncel_fiyat
                    islem_no    += 1
                    mesaj = (
                        f"📈 ALIM #{islem_no}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"Coin   : {sembol}\n"
                        f"Fiyat  : ${guncel_fiyat:,.0f}\n"
                        f"Miktar : {btc_miktar} BTC\n"
                        f"Harcama: ${harcama:.1f} USDT\n"
                        f"RSI    : {rsi_val:.1f}\n"
                        f"EMA50  : ${ema_val:,.0f}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"Hedef  : ${giris_fiyati * 1.05:,.0f} (+%5)\n"
                        f"Stop   : ${giris_fiyati * 0.975:,.0f} (-2.5%)"
                    )
                    print(mesaj)
                    telegram_gonder(mesaj)

            time.sleep(4 * 3600)

        except Exception as e:
            hata = f"❌ Hata: {str(e)}"
            print(hata)
            telegram_gonder(hata)
            time.sleep(60)

bot_calistir()


