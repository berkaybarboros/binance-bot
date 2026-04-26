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

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def telegram_gonder(mesaj):
    try:
        token = str(TELEGRAM_TOKEN).strip()
        chat_id = str(TELEGRAM_CHAT_ID).strip()
        url = "https://api.telegram.org/bot" + token + "/sendMessage"
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
    k = 2 / (periyot + 1)
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
        for v in hesap["balances"]:
            if v["asset"] == varlik:
                return float(v["free"])
    except Exception as e:
        print(f"Bakiye hata: {e}")
    return 0.0

def sinyal_uret(fiyatlar, hacimler):
    if len(fiyatlar) < 70:
        return "BEKLE", 0, 0
    rsi = hesapla_rsi(fiyatlar)
    ema50 = hesapla_ema(fiyatlar, 50)
    hacim_ort = hesapla_hacim_ort(hacimler)
    guncel = fiyatlar[-1]
    gun_hacim = hacimler[-1]
    al = (rsi < 55 and guncel > ema50 and gun_hacim > hacim_ort * 1.1)
    return ("AL" if al else "BEKLE"), rsi, ema50

def gunluk_ozet_gonder(ist, fiyat, rsi, bakiye, pozisyon_var):
    bugun = datetime.now().strftime("%d %B %Y")
    mesaj = (
        "Gunluk Ozet - " + bugun + "\n" +
        "----------------\n" +
        "BTC : $" + f"{fiyat:,.0f}" + "\n" +
        "RSI : " + f"{rsi:.1f}" + "\n" +
        "----------------\n" +
        "Islem : " + str(ist["bugun_islem"]) + "\n" +
        "Karli : " + str(ist["bugun_karli"]) + "\n" +
        "Zarar : " + str(ist["bugun_zararli"]) + "\n" +
        "K/Z   : $" + f"{ist['bugun_kar_zarar']:+.2f}" + "\n" +
        "----------------\n" +
        "Poz   : " + ("VAR" if pozisyon_var else "YOK") + "\n" +
        "Bakiye: $" + f"{bakiye:,.2f}" + "\n" +
        "----------------"
    )
    print(mesaj)
    telegram_gonder(mesaj)

def haftalik_ozet_gonder(ist, bakiye, baslangic):
    bugun = datetime.now().strftime("%d %B %Y")
    net = ((bakiye - baslangic) / baslangic) * 100
    mesaj = (
        "Haftalik Rapor - " + bugun + "\n" +
        "----------------\n" +
        "Islem : " + str(ist["hafta_islem"]) + "\n" +
        "Karli : " + str(ist["hafta_karli"]) + "\n" +
        "Zarar : " + str(ist["hafta_zararli"]) + "\n" +
        "K/Z   : $" + f"{ist['hafta_kar_zarar']:+.2f}" + "\n" +
        "----------------\n" +
        "Basl  : $" + f"{baslangic:,.2f}" + "\n" +
        "Su an : $" + f"{bakiye:,.2f}" + "\n" +
        "Getiri: %" + f"{net:+.2f}" + "\n" +
        "----------------"
    )
    print(mesaj)
    telegram_gonder(mesaj)

def bot_calistir():
    sembol = "BTCUSDT"
    pozisyon_var = False
    giris_fiyati = 0.0
    islem_no = 0
    baslangic_bakiye = bakiye_al("USDT")
    ist = {
        "bugun_islem": 0, "bugun_karli": 0,
        "bugun_zararli": 0, "bugun_kar_zarar": 0.0,
        "hafta_islem": 0, "hafta_karli": 0,
        "hafta_zararli": 0, "hafta_kar_zarar": 0.0,
    }
    son_gunluk = None
    son_haftalik = None

    basla = (
        "Bot basladi - Testnet\n" +
        "Strateji: RSI + EMA50 + Hacim\n" +
        "AL: RSI < 55\n" +
        "SAT: RSI > 60 / %5 kar / %2.5 stop\n" +
        "Gunluk: 09:00 / Haftalik: Pazartesi"
    )
    print(basla)
    telegram_gonder(basla)

    while True:
        try:
            simdi = datetime.now()
            zaman = simdi.strftime("%H:%M")
            fiyatlar, hacimler = veri_al(sembol)
            guncel_fiyat = fiyatlar[-1]
            rsi = hesapla_rsi(fiyatlar)
            ema50 = hesapla_ema(fiyatlar, 50)
            usdt_bakiye = bakiye_al("USDT")
            btc_bakiye = bakiye_al("BTC")

            print("[" + zaman + "] BTC:$" + f"{guncel_fiyat:,.0f}" +
                  " RSI:" + f"{rsi:.1f}" +
                  " USDT:$" + f"{usdt_bakiye:.0f}" +
                  " Poz:" + ("VAR" if pozisyon_var else "YOK"))

            bugun_str = simdi.strftime("%Y-%m-%d")
            hafta_str = simdi.strftime("%Y-W%W")

            if zaman >= "09:00" and son_gunluk != bugun_str:
                gunluk_ozet_gonder(ist, guncel_fiyat, rsi, usdt_bakiye, pozisyon_var)
                ist.update({"bugun_islem": 0, "bugun_karli": 0, "bugun_zararli": 0, "bugun_kar_zarar": 0.0})
                son_gunluk = bugun_str

            if simdi.weekday() == 0 and zaman >= "09:00" and son_haftalik != hafta_str:
                haftalik_ozet_gonder(ist, usdt_bakiye, baslangic_bakiye)
                ist.update({"hafta_islem": 0, "hafta_karli": 0, "hafta_zararli": 0, "hafta_kar_zarar": 0.0})
                son_haftalik = hafta_str

            if pozisyon_var:
                kar_yuzde = (guncel_fiyat - giris_fiyati) / giris_fiyati
                cikis = None
                if kar_yuzde >= 0.05:
                    cikis = "Kar al (+" + f"{kar_yuzde*100:.1f}" + "%)"
                elif kar_yuzde <= -0.025:
                    cikis = "Stop (" + f"{kar_yuzde*100:.1f}" + "%)"
                elif rsi > 60:
                    cikis = "RSI yuksek (" + f"{rsi:.1f}" + ")"
                if cikis:
                    btc_miktar = round(btc_bakiye * 0.99, 5)
                    if btc_miktar > 0:
                        client.order_market_sell(symbol=sembol, quantity=btc_miktar)
                        kar_usdt = btc_miktar * (guncel_fiyat - giris_fiyati)
                        pozisyon_var = False
                        ist["bugun_islem"] += 1
                        ist["hafta_islem"] += 1
                        ist["bugun_kar_zarar"] += kar_usdt
                        ist["hafta_kar_zarar"] += kar_usdt
                        if kar_usdt > 0:
                            ist["bugun_karli"] += 1
                            ist["hafta_karli"] += 1
                        else:
                            ist["bugun_zararli"] += 1
                            ist["hafta_zararli"] += 1
                        mesaj = (
                            "SATIS #" + str(islem_no) + "\n" +
                            "Sebep : " + cikis + "\n" +
                            "Fiyat : $" + f"{guncel_fiyat:,.0f}" + "\n" +
                            "Giris : $" + f"{giris_fiyati:,.0f}" + "\n" +
                            "K/Z   : $" + f"{kar_usdt:+.2f}" + "\n" +
                            "Bakiye: $" + f"{usdt_bakiye:.0f}"
                        )
                        print(mesaj)
                        telegram_gonder(mesaj)
            else:
                sinyal, rsi_val, ema_val = sinyal_uret(fiyatlar, hacimler)
                if sinyal == "AL" and usdt_bakiye > 10:
                    harcama = usdt_bakiye * 0.10
                    btc_miktar = round(harcama / guncel_fiyat, 5)
                    client.order_market_buy(symbol=sembol, quantity=btc_miktar)
                    pozisyon_var = True
                    giris_fiyati = guncel_fiyat
                    islem_no += 1
                    mesaj = (
                        "ALIM #" + str(islem_no) + "\n" +
                        "Fiyat : $" + f"{guncel_fiyat:,.0f}" + "\n" +
                        "Miktar: " + str(btc_miktar) + " BTC\n" +
                        "RSI   : " + f"{rsi_val:.1f}" + "\n" +
                        "Hedef : $" + f"{giris_fiyati * 1.05:,.0f}" + "\n" +
                        "Stop  : $" + f"{giris_fiyati * 0.975:,.0f}"
                    )
                    print(mesaj)
                    telegram_gonder(mesaj)

            time.sleep(4 * 3600)

        except Exception as e:
            hata = "Hata: " + str(e)
            print(hata)
            telegram_gonder(hata)
            time.sleep(60)

bot_calistir()
