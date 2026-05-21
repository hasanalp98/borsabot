import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import streamlit.components.v1 as components 
from streamlit_autorefresh import st_autorefresh

# --- 1. ARAYÜZ (STREAMLIT) AYARLARI ---
st.set_page_config(page_title="Borsa & Kripto Analiz Botu", layout="wide")
st.title("🚀 Kurumsal Seviye Canlı Analiz Paneli")

# --- AYARLAR MENÜSÜ (SOL PANEL) ---
st.sidebar.header("⚙️ Ayarlar")

piyasa_turu = st.sidebar.selectbox(
    "Piyasa Türü Seçin:",
    ["Borsa İstanbul (BIST)", "Kripto Paralar"],
    index=1 
)

otomatik_yenileme = st.sidebar.selectbox(
    "Canlı Akış (Yenileme Hızı):",
    ["Kapalı", "Canlı (5 Saniye)", "1 Dakika", "5 Dakika"],
    index=1 
)

yenileme_saniyesi = None
if otomatik_yenileme == "Canlı (5 Saniye)":
    yenileme_saniyesi = 5
elif otomatik_yenileme == "1 Dakika":
    yenileme_saniyesi = 60
elif otomatik_yenileme == "5 Dakika":
    yenileme_saniyesi = 300

# --- 🎯 TELEGRAM BİLDİRİM AYARLARI ---
TELEGRAM_TOKEN = "8941436007:AAEaJXcOKatL_jtJgVP9RIsZEmLIH7XJME0"
TELEGRAM_CHAT_ID = "8520995298"

if 'gonderilen_sinyaller' not in st.session_state:
    st.session_state.gonderilen_sinyaller = []

def telegram_mesaj_gonder(mesaj, sembol):
    if sembol not in st.session_state.gonderilen_sinyaller:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
            st.session_state.gonderilen_sinyaller.append(sembol)
        except Exception as e:
            pass

# --- 2. TAKİP LİSTELERİ ---
if piyasa_turu == "Borsa İstanbul (BIST)":
    turkiye_81_il = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"]
    takip_listesi = [
        "THYAO.IS", "ASELS.IS", "TUPRS.IS", "BIMAS.IS", "GARAN.IS", 
        "KCHOL.IS", "SAHOL.IS", "SISE.IS", "ISCTR.IS", "FROTO.IS", 
        "TOASO.IS", "HEKTS.IS", "SMRTG.IS", "ALARK.IS", "ARCLK.IS", 
        "ENJSA.IS", "ENKAI.IS", "PGSUS.IS"
    ]
else:
    takip_listesi = [
        "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "DOT-USD", 
        "LINK-USD", "AVAX-USD", "MATIC-USD", "SHIB-USD", "TRX-USD", "LTC-USD", "NEAR-USD", "UNI-USD", 
        "APT-USD", "STX-USD", "FIL-USD", "ATOM-USD", "IMX-USD", "HBAR-USD", "KAS-USD", "ETC-USD", 
        "ICP-USD", "XLM-USD", "GRT-USD", "OP-USD", "RENDER-USD", "INJ-USD", "SUI-USD", "RNDR-USD",
        "THETA-USD", "LDO-USD", "TIA-USD", "SEI-USD", "MKR-USD", "AAVE-USD", "EGLD-USD", "FET-USD", 
        "ALGO-USD", "FLOW-USD", "QNT-USD", "GALA-USD", "SAND-USD", "MANA-USD", "MINA-USD", "VET-USD", 
        "RUN-USD", "FTM-USD", "WIF-USD", "PEPE-USD", "FLOKI-USD", "BONK-USD", "JUP-USD", 
        "PYTH-USD", "DYDX-USD", "CRV-USD", "FXS-USD", "LRC-USD", "ENS-USD", "WOO-USD", "GMT-USD", 
        "RUNE-USD", "AGIX-USD", "OCEAN-USD", "AKT-USD", "CHZ-USD", "ZIL-USD", "BAT-USD", "ENJ-USD", 
        "ANKR-USD", "ONE-USD", "CELO-USD", "ROSE-USD", "RVN-USD", "WAVE-USD", "QTUM-USD",
        "AXS-USD", "APE-USD", "STMX-USD", "DENT-USD", "HOT-USD", "BTT-USD",
        "MASK-USD", "COMP-USD", "SNX-USD", "YFI-USD", "SUSHI-USD", "1INCH-USD", "ZEC-USD"
    ]

# --- 🧠 GEÇMİŞ VERİ ÖNBELLEĞI ---
@st.cache_data(ttl=300, show_spinner=False)
def gecmis_verileri_getir(sembol):
    v_1d = yf.download(sembol, period="6mo", interval="1d", progress=False)
    v_1h = yf.download(sembol, period="1mo", interval="1h", progress=False)
    return v_1d, v_1h

# --- 🌟 CANLI VERİ MOTORU (BİNANCE API & FRAGMENT) ---
@st.fragment(run_every=yenileme_saniyesi)
def canlı_tarama_motoru():
    tablo_verisi = []
    guclu_al_verenler = []
    
    binance_fiyatlar = {}
    if piyasa_turu == "Kripto Paralar":
        try:
            cevap = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=5).json()
            binance_fiyatlar = {item['symbol']: float(item['price']) for item in cevap}
        except:
            pass

    for sembol in takip_listesi:
        try:
            veri_1d, veri_1h = gecmis_verileri_getir(sembol)
            
            if veri_1d.empty or veri_1h.empty or len(veri_1d) < 20 or len(veri_1h) < 20:
                continue

            kapanis_1d = veri_1d['Close'].squeeze()
            if isinstance(kapanis_1d, pd.DataFrame): kapanis_1d = kapanis_1d.iloc[:, 0]
            
            hacim_1d = veri_1d['Volume'].squeeze()
            if isinstance(hacim_1d, pd.DataFrame): hacim_1d = hacim_1d.iloc[:, 0]
            
            yuksek_1d = veri_1d['High'].squeeze()
            if isinstance(yuksek_1d, pd.DataFrame): yuksek_1d = yuksek_1d.iloc[:, 0]
            
            dusuk_1d = veri_1d['Low'].squeeze()
            if isinstance(dusuk_1d, pd.DataFrame): dusuk_1d = dusuk_1d.iloc[:, 0]

            hisse_fiyati = float(kapanis_1d.iloc[-1])
            if piyasa_turu == "Kripto Paralar":
                binance_sembol = sembol.replace("-USD", "USDT")
                if binance_sembol in binance_fiyatlar:
                    hisse_fiyati = float(binance_fiyatlar[binance_sembol])
            
            sma5_1d = float(kapanis_1d.rolling(window=5).mean().iloc[-1])
            sma20_1d = float(kapanis_1d.rolling(window=20).mean().iloc[-1])
            
            fark_1d = kapanis_1d.diff()
            kazanc_1d = fark_1d.clip(lower=0).ewm(com=13, adjust=False).mean()
            kayip_1d = (-fark_1d.clip(upper=0)).ewm(com=13, adjust=False).mean()
            rsi_series_1d = 100 - (100 / (1 + (kazanc_1d / kayip_1d)))
            rsi_1d = float(rsi_series_1d.iloc[-1])
            
            macd_1d = (kapanis_1d.ewm(span=12, adjust=False).mean() - kapanis_1d.ewm(span=26, adjust=False).mean())
            macd_signal_1d = float(macd_1d.ewm(span=9, adjust=False).mean().iloc[-1])
            guncel_macd_1d = float(macd_1d.iloc[-1])
            
            hacim_sma20_1d = float(hacim_1d.rolling(window=20).mean().iloc[-1])
            guncel_hacim_1d = float(hacim_1d.iloc[-1])
            
            min_rsi_1d = rsi_series_1d.rolling(14).min()
            max_rsi_1d = rsi_series_1d.rolling(14).max()
            stoch_rsi_1d = ((rsi_series_1d - min_rsi_1d) / (max_rsi_1d - min_rsi_1d)) * 100
            stoch_k_1d = float(stoch_rsi_1d.rolling(3).mean().iloc[-1])
            stoch_d_1d = float(stoch_rsi_1d.rolling(3).mean().rolling(3).mean().iloc[-1])
            
            std_20_1d = float(kapanis_1d.rolling(20).std().iloc[-1])
            bollinger_alt_1d = sma20_1d - (2 * std_20_1d)
            
            kapanis_prev_1d = kapanis_1d.shift(1)
            tr1_1d = yuksek_1d - dusuk_1d
            tr2_1d = (yuksek_1d - kapanis_prev_1d).abs()
            tr3_1d = (dusuk_1d - kapanis_prev_1d).abs()
            true_range_1d = pd.concat([tr1_1d, tr2_1d, tr3_1d], axis=1).max(axis=1)
            atr_1d = float(true_range_1d.rolling(14).mean().iloc[-1])
            
            puan_1d = 0
            if sma5_1d > sma20_1d: puan_1d += 1 
            if 30 < rsi_1d < 65: puan_1d += 1 
            if guncel_macd_1d > macd_signal_1d: puan_1d += 1 
            if guncel_hacim_1d > hacim_sma20_1d: puan_1d += 1 
            if stoch_k_1d > stoch_d_1d and stoch_k_1d < 50: puan_1d += 1 
            if hisse_fiyati <= (bollinger_alt_1d * 1.05): puan_1d += 1 
            
            kapanis_1h = veri_1h['Close'].squeeze()
            if isinstance(kapanis_1h, pd.DataFrame): kapanis_1h = kapanis_1h.iloc[:, 0]
            
            hacim_1h = veri_1h['Volume'].squeeze()
            if isinstance(hacim_1h, pd.DataFrame): hacim_1h = hacim_1h.iloc[:, 0]
            
            yuksek_1h = veri_1h['High'].squeeze()
            if isinstance(yuksek_1h, pd.DataFrame): yuksek_1h = yuksek_1h.iloc[:, 0]
            
            dusuk_1h = veri_1h['Low'].squeeze()
            if isinstance(dusuk_1h, pd.DataFrame): dusuk_1h = dusuk_1h.iloc[:, 0]

            sma5_1h = float(kapanis_1h.rolling(window=5).mean().iloc[-1])
            sma20_1h = float(kapanis_1h.rolling(window=20).mean().iloc[-1])
            
            fark_1h = kapanis_1h.diff()
            kazanc_1h = fark_1h.clip(lower=0).ewm(com=13, adjust=False).mean()
            kayip_1h = (-fark_1h.clip(upper=0)).ewm(com=13, adjust=False).mean()
            rsi_series_1h = 100 - (100 / (1 + (kazanc_1h / kayip_1h)))
            rsi_1h = float(rsi_series_1h.iloc[-1])
            
            macd_1h = (kapanis_1h.ewm(span=12, adjust=False).mean() - kapanis_1h.ewm(span=26, adjust=False).mean())
            macd_signal_1h = float(macd_1h.ewm(span=9, adjust=False).mean().iloc[-1])
            guncel_macd_1h = float(macd_1h.iloc[-1])
            
            hacim_sma20_1h = float(hacim_1h.rolling(window=20).mean().iloc[-1])
            guncel_hacim_1h = float(hacim_1h.iloc[-1])
            
            min_rsi_1h = rsi_series_1h.rolling(14).min()
            max_rsi_1h = rsi_series_1h.rolling(14).max()
            stoch_rsi_1h = ((rsi_series_1h - min_rsi_1h) / (max_rsi_1h - min_rsi_1h)) * 100
            stoch_k_1h = float(stoch_rsi_1h.rolling(3).mean().iloc[-1])
            stoch_d_1h = float(stoch_rsi_1h.rolling(3).mean().rolling(3).mean().iloc[-1])
            
            std_20_1h = float(kapanis_1h.rolling(20).std().iloc[-1])
            bollinger_alt_1h = sma20_1h - (2 * std_20_1h)
            
            puan_1h = 0
            if sma5_1h > sma20_1h: puan_1h += 1 
            if 30 < rsi_1h < 65: puan_1h += 1 
            if guncel_macd_1h > macd_signal_1h: puan_1h += 1 
            if guncel_hacim_1h > hacim_sma20_1h: puan_1h += 1 
            if stoch_k_1h > stoch_d_1h and stoch_k_1h < 50: puan_1h += 1 
            if hisse_fiyati <= (bollinger_alt_1h * 1.05): puan_1h += 1 
            
            satis_hedefi = hisse_fiyati + (atr_1d * 2)
            alis_hedefi_stop = hisse_fiyati - (atr_1d * 1.5)
            
            if piyasa_turu == "Kripto Paralar":
                fiyat_format = f"{hisse_fiyati:.10f}"
                stop_format = f"{alis_hedefi_stop:.10f}"
                kar_format = f"{satis_hedefi:.10f}"
            else:
                fiyat_format = f"{hisse_fiyati:.4f}" if hisse_fiyati < 1.0 else f"{hisse_fiyati:.2f}"
                stop_format = f"{alis_hedefi_stop:.4f}" if hisse_fiyati < 1.0 else f"{alis_hedefi_stop:.2f}"
                kar_format = f"{satis_hedefi:.4f}" if hisse_fiyati < 1.0 else f"{satis_hedefi:.2f}"

            if puan_1d >= 4 and puan_1h >= 4:
                final_sinyal = "🔥 ÇİFTE ONAYLI GÜÇLÜ AL"
                guclu_al_verenler.append(f"⭐ {sembol}: {fiyat_format} (Hedef: {kar_format}) | Puan: G:{puan_1d}/6 S:{puan_1h}/6")
                
                bildirim_mesaji = f"🎯 *CANLI ÇİFTE ONAY YAKALANDI!*\n\n• Varlık: {sembol}\n• Durum: GÜÇLÜ AL\n• Canlı Fiyat: {fiyat_format}\n• Kâr Al (+2 ATR): {kar_format}\n• Stop Kes (-1.5 ATR): {stop_format}"
                telegram_mesaj_gonder(bildirim_mesaji, sembol)
                
            elif puan_1d >= 4:
                final_sinyal = "📈 Sadece Günlükte Al"
            elif puan_1h >= 4:
                final_sinyal = "⏱️ Sadece Saatlikte Al"
            else:
                final_sinyal = "❌ Nötr / Sat"
            
            tablo_verisi.append({
                "VARLIK (SEMBOL)": sembol,
                "CANLI FİYAT": fiyat_format,
                "DİNAMİK STOP": stop_format,
                "DİNAMİK HEDEF": kar_format,
                "GÜNLÜK RSI": f"{rsi_1d:.1f}",
                "GÜNLÜK PUAN": f"{puan_1d}/6",
                "SAATLİK RSI": f"{rsi_1h:.1f}",
                "SAATLİK PUAN": f"{puan_1h}/6",
                "FİNAL DURUM": final_sinyal
            })
            
        except Exception as e:
            pass

    st.subheader(f"📊 {piyasa_turu} Kesintisiz Canlı Fiyat Tablosu")
    if tablo_verisi:
        df = pd.DataFrame(tablo_verisi)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Canlı veriler yükleniyor...")

    st.divider()

    st.subheader("🎯 Canlı İşlem Fırsatları (6 İndikatörlü)")
    if guclu_al_verenler:
        for hisse in guclu_al_verenler:
            st.success(hisse)
    else:
        st.warning("Şu an hem GÜNLÜK hem de SAATLİK grafikte (En az 4/6 puanla) ÇİFTE ONAY alan varlık bulunamadı. Akış izleniyor...")

if yenileme_saniyesi:
    st.sidebar.caption(f"🟢 Canlı Veri Akışı Aktif (Her {yenileme_saniyesi} Saniyede Güncellenir)")

# Motoru Başlatıyoruz
canlı_tarama_motoru()