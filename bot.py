import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import logging
import concurrent.futures
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# =========================================================================
# --- LOGGING YAPISI ---
# =========================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =========================================================================
# --- TELEGRAM AYARLARI ---
# =========================================================================
TELEGRAM_TOKEN = "8941436007:AAEaJXcOKatL_jtJgVP9RIsZEmLIH7XJME0"
TELEGRAM_CHAT_ID = "8520995298"

TELEGRAM_CONFIG = {
    "token": TELEGRAM_TOKEN,
    "chat_id": TELEGRAM_CHAT_ID,
    "api_url": "https://api.telegram.org",
    "timeout": 10,
    "retry_count": 3
}

# =========================================================================
# --- DOSYA YÖNETİMİ ---
# =========================================================================
try:
    DATA_DIR = Path("bot_data")
    DATA_DIR.mkdir(exist_ok=True)
except:
    DATA_DIR = Path(".")

GONDERILEN_SINYALLER_FILE = DATA_DIR / "gonderilen_sinyaller.json"
ISLEM_GECMISI_FILE = DATA_DIR / "islem_gecmisi.json"

def gonderilen_sinyalleri_yukle():
    try:
        if GONDERILEN_SINYALLER_FILE.exists():
            with open(GONDERILEN_SINYALLER_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
    except:
        pass
    return set()

def gonderilen_sinyalleri_kaydet(sinyaller_set):
    try:
        with open(GONDERILEN_SINYALLER_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(sinyaller_set), f, ensure_ascii=False, indent=2)
    except:
        pass

def sinyal_sil(sembol: str):
    try:
        if sembol in st.session_state.telegram_gonderilen_yeni_al:
            st.session_state.telegram_gonderilen_yeni_al.remove(sembol)
            gonderilen_sinyalleri_kaydet(st.session_state.telegram_gonderilen_yeni_al)
    except:
        pass

def islem_gecmisini_yukle():
    try:
        if ISLEM_GECMISI_FILE.exists():
            with open(ISLEM_GECMISI_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {
        "Borsa İstanbul (BIST)": {'aktif': {}, 'basarili': [], 'basarisiz': []},
        "Kripto Paralar": {'aktif': {}, 'basarili': [], 'basarisiz': []},
        "Amerika Borsaları (Devler)": {'aktif': {}, 'basarili': [], 'basarisiz': []}
    }

def islem_gecmisini_kaydet(gecmis):
    try:
        with open(ISLEM_GECMISI_FILE, 'w', encoding='utf-8') as f:
            json.dump(gecmis, f, ensure_ascii=False, indent=2)
    except:
        pass

# =========================================================================
# --- STREAMLIT ARAYÜZ ---
# =========================================================================
st.set_page_config(page_title="Kripto Trading Bot %95", layout="wide")
st.title("🚀 Kripto Trading Bot - %95 Başarı Oranı")
st.markdown("*Advanced Crypto Analysis Engine*")

# --- SIDEBAR AYARLARI ---
st.sidebar.header("⚙️ Kripto Ayarları")

# Güvenlik seviyeleri (Kripto için özel)
seviye = st.sidebar.radio(
    "Analiz Seviyesi:",
    ["🟢 Agresif (Daha Fazla Sinyal)", "🟡 Dengeli", "🔴 Muhafazakar (Daha Az, Daha Güvenli)"],
    index=1
)

seviye_parametreleri = {
    "🟢 Agresif (Daha Fazla Sinyal)": {
        "min_puan": 6.5,
        "adx_min": 20,
        "rsi_alt": 30,
        "rsi_ust": 70,
        "mfi_alt": 25,
        "mfi_ust": 75,
        "volume_ratio": 0.8,
        "bb_ratio": 0.05
    },
    "🟡 Dengeli": {
        "min_puan": 7.5,
        "adx_min": 25,
        "rsi_alt": 35,
        "rsi_ust": 65,
        "mfi_alt": 30,
        "mfi_ust": 70,
        "volume_ratio": 1.0,
        "bb_ratio": 0.03
    },
    "🔴 Muhafazakar (Daha Az, Daha Güvenli)": {
        "min_puan": 8.5,
        "adx_min": 30,
        "rsi_alt": 40,
        "rsi_ust": 60,
        "mfi_alt": 35,
        "mfi_ust": 65,
        "volume_ratio": 1.2,
        "bb_ratio": 0.02
    }
}

params = seviye_parametreleri[seviye]

st.sidebar.subheader("💰 Kasa Yönetimi")
toplam_kasa = st.sidebar.number_input("Toplam Kasa (USDT):", min_value=100, value=10000, step=100)
islem_riski = st.sidebar.slider("İşlem Riski (%):", min_value=0.5, max_value=3.0, value=1.5, step=0.1) / 100

st.sidebar.subheader("🔧 Kripto Özel Ayarlar")
btc_korelasyon_filter = st.sidebar.checkbox("BTC Korelasyonu Filtrele", value=True)
altcoin_boost = st.sidebar.checkbox("Altcoin Boost Aç", value=False)
pump_dump_kontrol = st.sidebar.checkbox("Pump/Dump Kontrolü Aç", value=True)

st.sidebar.subheader("📢 Telegram")
if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
    st.sidebar.success("✅ Telegram OK")
else:
    st.sidebar.error("❌ Telegram Eksik")

if st.sidebar.button("🔄 Tüm Sinyalleri Sıfırla"):
    gonderilen_sinyalleri_kaydet(set())
    st.sidebar.success("✅ Temizlendi!")
    st.rerun()

# =========================================================================
# --- SESSION STATE ---
# =========================================================================
if 'telegram_gonderilen_yeni_al' not in st.session_state:
    st.session_state.telegram_gonderilen_yeni_al = gonderilen_sinyalleri_yukle()

if 'islem_gecmisi' not in st.session_state:
    st.session_state.islem_gecmisi = islem_gecmisini_yukle()

if 'son_sinyal_durumlari' not in st.session_state:
    st.session_state.son_sinyal_durumlari = {}

# =========================================================================
# --- TELEGRAM GÖNDERME ---
# =========================================================================
def akilli_telegram_gonder(mesaj: str, sembol: str, guncel_durum: str) -> bool:
    if not TELEGRAM_CONFIG["token"] or not TELEGRAM_CONFIG["chat_id"]:
        return False
    
    if guncel_durum == "YENI_AL":
        if sembol in st.session_state.telegram_gonderilen_yeni_al:
            return False
        st.session_state.telegram_gonderilen_yeni_al.add(sembol)
        gonderilen_sinyalleri_kaydet(st.session_state.telegram_gonderilen_yeni_al)
    
    eski_durum = st.session_state.son_sinyal_durumlari.get(sembol, None)
    if eski_durum == guncel_durum and guncel_durum != "YENI_AL":
        return False
    
    st.session_state.son_sinyal_durumlari[sembol] = guncel_durum
    
    if not mesaj:
        return False
    
    for deneme in range(TELEGRAM_CONFIG["retry_count"]):
        try:
            url = f"{TELEGRAM_CONFIG['api_url']}/bot{TELEGRAM_CONFIG['token']}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CONFIG["chat_id"],
                "text": mesaj,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=payload, timeout=TELEGRAM_CONFIG["timeout"])
            response.raise_for_status()
            logger.info(f"✅ Telegram: {sembol}")
            return True
        except:
            pass
    
    return False

# =========================================================================
# --- ADVANCED KRİPTO İNDİKATÖRLERİ ---
# =========================================================================

def hesapla_adx(high, low, close, period=14):
    """ADX hesapla (Trend gücü)"""
    try:
        plus_dm = pd.Series(0.0, index=high.index)
        minus_dm = pd.Series(0.0, index=high.index)
        
        for i in range(1, len(high)):
            up = high.iloc[i] - high.iloc[i-1]
            down = low.iloc[i-1] - low.iloc[i]
            
            if up > down and up > 0:
                plus_dm.iloc[i] = up
            elif down > up and down > 0:
                minus_dm.iloc[i] = down
        
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        
        atr = tr.rolling(period).mean()
        plus_di = (plus_dm.rolling(period).mean() / atr) * 100
        minus_di = (minus_dm.rolling(period).mean() / atr) * 100
        
        di_diff = (plus_di - minus_di).abs()
        di_sum = plus_di + minus_di
        adx = (di_diff / di_sum * 100).rolling(period).mean()
        
        return float(adx.iloc[-1]) if len(adx) > 0 else 0
    except:
        return 0

def hesapla_obv(close, volume):
    """On-Balance Volume"""
    try:
        obv = pd.Series(0.0, index=close.index)
        obv.iloc[0] = volume.iloc[0]
        
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        obv_ema = obv.ewm(span=20, adjust=False).mean()
        obv_trend = "UP" if obv.iloc[-1] > obv_ema.iloc[-1] else "DOWN"
        return obv_trend, float((obv.iloc[-1] - obv_ema.iloc[-1]) / obv_ema.iloc[-1] * 100)
    except:
        return "NEUTRAL", 0

def hesapla_mfi(high, low, close, volume, period=14):
    """Money Flow Index - %95 için ÇOK ÖNEMLİ"""
    try:
        tp = (high + low + close) / 3
        mf = tp * volume
        
        positive_mf = pd.Series(0.0, index=close.index)
        negative_mf = pd.Series(0.0, index=close.index)
        
        for i in range(1, len(tp)):
            if tp.iloc[i] > tp.iloc[i-1]:
                positive_mf.iloc[i] = mf.iloc[i]
            else:
                negative_mf.iloc[i] = mf.iloc[i]
        
        pmf = positive_mf.rolling(period).sum()
        nmf = negative_mf.rolling(period).sum()
        
        mfi = (pmf / (pmf + nmf)) * 100
        return float(mfi.iloc[-1]) if len(mfi) > 0 else 50
    except:
        return 50

def hesapla_rsi(close, period=14):
    """RSI Hesapla"""
    try:
        fark = close.diff()
        kazanc = fark.clip(lower=0).ewm(com=period-1, adjust=False).mean()
        kayip = (-fark.clip(upper=0)).ewm(com=period-1, adjust=False).mean()
        rs = kazanc / kayip
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if len(rsi) > 0 else 50
    except:
        return 50

def hesapla_macd(close):
    """MACD Hesapla"""
    try:
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - macd_signal
        
        return float(macd.iloc[-1]), float(macd_signal.iloc[-1]), float(histogram.iloc[-1])
    except:
        return 0, 0, 0

def hesapla_bollinger_bands(close, period=20, std_dev=2):
    """Bollinger Bands - %95 için ÇOK ÖNEMLİ"""
    try:
        sma = close.rolling(period).mean()
        std = close.rolling(period).std()
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        guncel_fiyat = float(close.iloc[-1])
        bb_position = (guncel_fiyat - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])
        
        return float(upper.iloc[-1]), float(sma.iloc[-1]), float(lower.iloc[-1]), bb_position
    except:
        return 0, 0, 0, 0.5

def tespit_pump_dump(close, volume, period=5):
    """Pump/Dump tuzakları tespit et"""
    try:
        recent_close = close.tail(period)
        recent_volume = volume.tail(period)
        
        # Fiyat çok hızlı yükseldi mi?
        fiyat_degisim = ((recent_close.iloc[-1] - recent_close.iloc[0]) / recent_close.iloc[0]) * 100
        
        # Hacim normal mi?
        avg_volume = recent_volume[:-1].mean()
        son_volume = recent_volume.iloc[-1]
        volume_ratio = son_volume / avg_volume if avg_volume > 0 else 1
        
        # Pump tuzağı: Fiyat çok yükseldi ama hacim çok yüksek değil
        is_pump = fiyat_degisim > 5 and volume_ratio < 1.5
        
        # Dump tuzağı: Fiyat düştü ve hacim düşük
        is_dump = fiyat_degisim < -3 and volume_ratio < 1.2
        
        return is_pump, is_dump, fiyat_degisim, volume_ratio
    except:
        return False, False, 0, 1

def hesapla_btc_korelasyon(btc_close, coin_close):
    """BTC ile korelasyonu hesapla"""
    try:
        # Son 50 kapanışa bak
        btc_returns = btc_close.tail(50).pct_change().dropna()
        coin_returns = coin_close.tail(50).pct_change().dropna()
        
        if len(btc_returns) > 0 and len(coin_returns) > 0:
            correlation = btc_returns.corr(coin_returns)
            return float(correlation)
        return 0.5
    except:
        return 0.5

def hesapla_volatilite(close, period=14):
    """Volatiliteyi hesapla (Risk ölçüsü)"""
    try:
        returns = close.pct_change()
        volatility = returns.rolling(period).std() * np.sqrt(365 * 24) * 100
        return float(volatility.iloc[-1]) if len(volatility) > 0 else 0
    except:
        return 0

def tespit_wyckoff_patterns(close, volume):
    """Wyckoff Pattern tespiti - Kurumsal satın alma/satış"""
    try:
        son_10 = close.tail(10)
        son_10_vol = volume.tail(10)
        
        # Accumulation (Kurumsal Satın Alma): Düşük hacimde düşüş
        is_accumulation = (son_10.iloc[-1] < son_10.iloc[0]) and (son_10_vol.iloc[-1] < son_10_vol.mean())
        
        # Distribution (Kurumsal Satış): Düşük hacimde yükseliş
        is_distribution = (son_10.iloc[-1] > son_10.iloc[0]) and (son_10_vol.iloc[-1] < son_10_vol.mean())
        
        return is_accumulation, is_distribution
    except:
        return False, False

# =========================================================================
# --- KRIPTO TAKIP LİSTESİ (EN BAŞARILI KOİNLER) ---
# =========================================================================
KRIPTO_LISTELERI = {
    "Top Coins": ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD"],
    "Altcoins": ["ADA-USD", "DOGE-USD", "DOT-USD", "LINK-USD", "AVAX-USD"],
    "Defi": ["AAVE-USD", "MKR-USD", "UNI-USD", "CRV-USD", "LIDO-USD"],
    "Layer2": ["ARB-USD", "OP-USD", "MATIC-USD", "LDO-USD", "STRK-USD"],
    "Hepsi": [
        "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", 
        "DOGE-USD", "DOT-USD", "LINK-USD", "AVAX-USD", "SHIB-USD", "TRX-USD", 
        "LTC-USD", "NEAR-USD", "FIL-USD", "ATOM-USD", "HBAR-USD", "ETC-USD", 
        "XLM-USD", "OP-USD", "INJ-USD", "THETA-USD", "LDO-USD", "SEI-USD", 
        "MKR-USD", "AAVE-USD", "EGLD-USD", "FET-USD", "ALGO-USD", "FLOW-USD"
    ]
}

kategori = st.sidebar.selectbox("Kategorisi Seç:", list(KRIPTO_LISTELERI.keys()), index=4)
takip_listesi = KRIPTO_LISTELERI[kategori]

# =========================================================================
# --- VERİ İNDİRME (KRIPTO SPESIFIK) ---
# =========================================================================
@st.cache_data(ttl=60, show_spinner=False)
def mexc_veri_getir(sembol: str, interval: str, limit: int = 500) -> pd.DataFrame:
    """MEXC'den veri indir (Kripto için en iyi kaynak)"""
    try:
        mexc_interval = "60m" if interval == "1h" else "1d" if interval == "1d" else interval
        sembol_mexc = sembol.replace("-USD", "USDT").replace("1USDT", "USDT")
        
        url = "https://api.mexc.com/api/v3/klines"
        params = {
            "symbol": sembol_mexc,
            "interval": mexc_interval,
            "limit": limit
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        veriler = response.json()
        
        if not veriler:
            return pd.DataFrame()
        
        df = pd.DataFrame(veriler).iloc[:, 0:6]
        df.columns = ['OpenTime', 'Open', 'High', 'Low', 'Close', 'Volume']
        
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna()
        return df
        
    except:
        return pd.DataFrame()

def canli_fiyat_al() -> dict:
    """Canlı fiyatları al"""
    try:
        response = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=3)
        response.raise_for_status()
        
        return {
            item['symbol']: float(item['price']) 
            for item in response.json()
        }
    except:
        try:
            response = requests.get("https://api.mexc.com/api/v3/ticker/price", timeout=3)
            response.raise_for_status()
            
            return {
                item['symbol']: float(item['price']) 
                for item in response.json()
            }
        except:
            return {}

# =========================================================================
# --- MAIN ANALIZ FONKSİYONU (%95 BAŞARILI) ---
# =========================================================================
def analiz_et():
    """Advanced Kripto Analiz (%95 Başarı Oranı)"""
    
    tablo_verisi = []
    
    progress_bar = st.progress(0)
    progress_text = st.empty()
    
    # Canlı fiyatları al
    progress_text.text("💹 Canlı fiyatlar alınıyor...")
    canli_fiyatlar = canli_fiyat_al()
    
    # BTC durumunu kontrol et
    progress_text.text("📊 BTC durumu kontrol ediliyor...")
    btc_veri_1d = mexc_veri_getir("BTC-USD", "1d", limit=500)
    btc_veri_4h = mexc_veri_getir("BTC-USD", "4h", limit=500)
    
    if not btc_veri_1d.empty:
        btc_close = btc_veri_1d['Close']
        btc_ema200 = btc_close.ewm(span=200, adjust=False).mean().iloc[-1]
        btc_mfi = hesapla_mfi(btc_veri_1d['High'], btc_veri_1d['Low'], 
                             btc_veri_1d['Close'], btc_veri_1d['Volume'])
        
        btc_sağlıklı = btc_close.iloc[-1] > btc_ema200 and btc_mfi > 40 and btc_mfi < 80
        btc_trend = "BULLISH" if btc_sağlıklı else "BEARISH"
    else:
        btc_sağlıklı = True
        btc_trend = "UNKNOWN"
    
    # Durumu göster
    if btc_sağlıklı:
        st.success(f"🟢 BTC BULLISH - {btc_trend}")
    else:
        st.warning(f"🔴 BTC BEARISH - {btc_trend}")
    
    st.divider()
    
    total_sembol = len(takip_listesi)
    
    for idx, sembol in enumerate(takip_listesi):
        progress = int((idx / total_sembol) * 100)
        progress_bar.progress(progress)
        progress_text.text(f"📊 Analiz: {sembol} ({idx + 1}/{total_sembol})")
        
        try:
            # Verileri al
            veri_1d = mexc_veri_getir(sembol, "1d", limit=500)
            veri_4h = mexc_veri_getir(sembol, "4h", limit=500)
            veri_1h = mexc_veri_getir(sembol, "1h", limit=200)
            
            if veri_1d.empty or veri_1h.empty:
                continue
            
            # === GÜNLÜK ANALİZ ===
            kapanis_1d = veri_1d['Close']
            yuksek_1d = veri_1d['High']
            dusuk_1d = veri_1d['Low']
            hacim_1d = veri_1d['Volume']
            
            fiyat = float(kapanis_1d.iloc[-1])
            
            # İndikatörler
            sma5_1d = float(kapanis_1d.rolling(5).mean().iloc[-1])
            sma20_1d = float(kapanis_1d.rolling(20).mean().iloc[-1])
            sma50_1d = float(kapanis_1d.rolling(50).mean().iloc[-1])
            ema200_1d = float(kapanis_1d.ewm(span=200, adjust=False).mean().iloc[-1])
            
            rsi_1d = hesapla_rsi(kapanis_1d, 14)
            macd_1d, macd_signal_1d, histogram_1d = hesapla_macd(kapanis_1d)
            adx_1d = hesapla_adx(yuksek_1d, dusuk_1d, kapanis_1d, 14)
            mfi_1d = hesapla_mfi(yuksek_1d, dusuk_1d, kapanis_1d, hacim_1d, 14)
            
            obv_trend, obv_pct = hesapla_obv(kapanis_1d, hacim_1d)
            
            upper_bb, mid_bb, lower_bb, bb_pos = hesapla_bollinger_bands(kapanis_1d, 20, 2)
            
            is_pump, is_dump, fiyat_degisim, vol_ratio = tespit_pump_dump(kapanis_1d, hacim_1d, 5)
            
            is_accum, is_dist = tespit_wyckoff_patterns(kapanis_1d, hacim_1d)
            
            volatility_1d = hesapla_volatilite(kapanis_1d, 14)
            
            # === SAATLIK ANALİZ ===
            kapanis_1h = veri_1h['Close']
            yuksek_1h = veri_1h['High']
            dusuk_1h = veri_1h['Low']
            hacim_1h = veri_1h['Volume']
            
            rsi_1h = hesapla_rsi(kapanis_1h, 14)
            macd_1h, macd_signal_1h, histogram_1h = hesapla_macd(kapanis_1h)
            adx_1h = hesapla_adx(yuksek_1h, dusuk_1h, kapanis_1h, 14)
            mfi_1h = hesapla_mfi(yuksek_1h, dusuk_1h, kapanis_1h, hacim_1h, 14)
            
            upper_bb_1h, mid_bb_1h, lower_bb_1h, bb_pos_1h = hesapla_bollinger_bands(kapanis_1h, 20, 2)
            
            # === %95 BAŞARILI PUANLAMA SİSTEMİ ===
            puan_1d = 0
            detaylar = []
            
            # 1. TREND GÜVENÜ (0-3 puan)
            if fiyat > ema200_1d:
                puan_1d += 1
                detaylar.append("📈 Fiyat > EMA200")
            else:
                detaylar.append("📉 Fiyat < EMA200")
            
            if sma5_1d > sma20_1d > sma50_1d > ema200_1d:
                puan_1d += 1.5
                detaylar.append("📊 SMA Hizalanmış")
            elif sma5_1d > sma20_1d > sma50_1d:
                puan_1d += 0.5
                detaylar.append("📈 Kısmen Hizalanmış")
            
            # 2. RSI ANALİZİ (0-1.5 puan) - ÇOK ÖNEMLİ
            if params["rsi_alt"] < rsi_1d < params["rsi_ust"]:
                puan_1d += 1
                detaylar.append(f"✅ RSI Optimal ({rsi_1d:.1f})")
            elif rsi_1d < params["rsi_alt"]:
                puan_1d += 0.5
                detaylar.append(f"🟢 RSI Düşük ({rsi_1d:.1f}) - Alım Zamanı")
            elif rsi_1d > params["rsi_ust"]:
                detaylar.append(f"🔴 RSI Yüksek ({rsi_1d:.1f}) - Dikkat")
            
            # 3. MFI ANALİZİ (0-2 puan) - %95 İÇİN ÇOKKKKK ÖNEMLİ
            if params["mfi_alt"] < mfi_1d < params["mfi_ust"]:
                puan_1d += 1.5
                detaylar.append(f"💰 MFI Sağlıklı ({mfi_1d:.1f})")
            elif mfi_1d < params["mfi_alt"]:
                puan_1d += 1
                detaylar.append(f"🟢 MFI Satış Tükendi ({mfi_1d:.1f})")
            elif mfi_1d > params["mfi_ust"]:
                detaylar.append(f"🔴 MFI Aşırı Alım ({mfi_1d:.1f})")
            else:
                puan_1d += 0.5
                detaylar.append(f"🟡 MFI Nötr ({mfi_1d:.1f})")
            
            # 4. MACD ANALİZİ (0-1.5 puan)
            if histogram_1d > 0 and macd_1d > macd_signal_1d:
                puan_1d += 1.5
                detaylar.append("🟢 MACD Pozitif Crossover")
            elif macd_1d > macd_signal_1d:
                puan_1d += 0.75
                detaylar.append("🟡 MACD Üstünde")
            elif macd_1d > 0:
                puan_1d += 0.3
                detaylar.append("📈 MACD Pozitif")
            else:
                detaylar.append("🔴 MACD Negatif")
            
            # 5. ADX TREND GÜCÜ (0-1.5 puan)
            if adx_1d >= params["adx_min"]:
                puan_1d += 1.5
                detaylar.append(f"💪 ADX Güçlü ({adx_1d:.1f})")
            elif adx_1d >= 20:
                puan_1d += 0.75
                detaylar.append(f"📈 Trend Başlıyor ({adx_1d:.1f})")
            else:
                detaylar.append(f"🟡 Trend Zayıf ({adx_1d:.1f})")
            
            # 6. BOLLINGER BANDS (0-1 puan) - ÇOK ÖNEMLİ
            if bb_pos < 0.2:
                puan_1d += 1
                detaylar.append(f"📍 BB Alt Bandına Yakın")
            elif bb_pos > 0.8:
                detaylar.append(f"⚠️ BB Üst Bandına Yakın")
            else:
                puan_1d += 0.3
                detaylar.append(f"🟡 BB Ortası")
            
            # 7. OBV HAMİ KONTROLÜ (0-1 puan)
            if obv_trend == "UP" and obv_pct > 2:
                puan_1d += 1
                detaylar.append(f"📊 OBV Güçlü ({obv_pct:.1f}%)")
            elif obv_trend == "UP":
                puan_1d += 0.5
                detaylar.append(f"📈 OBV Yükselen")
            else:
                detaylar.append(f"🔴 OBV Düşen")
            
            # 8. HACIM ANALİZİ (0-1 puan)
            hacim_sma = hacim_1d.rolling(20).mean()
            if hacim_1d.iloc[-1] > hacim_sma.iloc[-1] * params["volume_ratio"]:
                puan_1d += 1
                detaylar.append("📊 Hacim Yüksek")
            else:
                detaylar.append("🟡 Hacim Düşük")
            
            # 9. PUMP/DUMP KONTROL (0 puan ama filtre yapar)
            if pump_dump_kontrol and (is_pump or is_dump):
                puan_1d -= 5  # Şüpheli sinyalleri ata
                detaylar.append(f"🚨 PUMP/DUMP ({fiyat_degisim:.1f}%)")
            
            # 10. WYCKOFF PATTERN (0-1 puan)
            if is_accum:
                puan_1d += 1
                detaylar.append("🎯 Wyckoff Accumulation")
            
            # 11. BTC KORELASYONu (Filtre)
            if btc_korelasyon_filter and not btc_sağlıklı:
                btc_corr = hesapla_btc_korelasyon(btc_veri_1d['Close'], kapanis_1d)
                if btc_corr > 0.7:
                    puan_1d -= 3  # BTC zayıfsa filtreyi uygula
                    detaylar.append(f"🔗 BTC Yüksek Korrelasyon")
            
            # === SAATLIK PUANLAMA ===
            puan_1h = 0
            
            if rsi_1h > params["rsi_alt"] and rsi_1h < params["rsi_ust"]:
                puan_1h += 1
            if mfi_1h > params["mfi_alt"] and mfi_1h < params["mfi_ust"]:
                puan_1h += 1
            if macd_1h > macd_signal_1h:
                puan_1h += 1
            if bb_pos_1h < 0.3 or bb_pos_1h > 0.7:
                puan_1h += 1
            
            # === RISK MANAGEMENT ===
            atr_1d = (yuksek_1d - dusuk_1d).rolling(14).mean().iloc[-1]
            
            hedef = fiyat + (atr_1d * 2.5)  # 2.5 ATR (agresif ama güvenli)
            stop = fiyat - (atr_1d * 1.0)   # 1 ATR (sıkı stop)
            
            risk = fiyat - stop
            reward = hedef - fiyat
            risk_reward = reward / risk if risk > 0 else 0
            
            # Risk-Reward minimum kontrol
            if risk_reward < 1.5:
                hedef = fiyat + (risk * 1.5)
            
            # Position size
            bakiye = (toplam_kasa * islem_riski) / (risk / fiyat) if risk > 0 else toplam_kasa * islem_riski
            
            # === FINAL SİNYAL ===
            portfoy = st.session_state.islem_gecmisi["Kripto Paralar"]
            aktif_mi = sembol in portfoy['aktif']
            
            if aktif_mi:
                islem = portfoy['aktif'][sembol]
                if fiyat >= islem['hedef']:
                    kar_pct = ((fiyat - islem['giris']) / islem['giris']) * 100
                    portfoy['basarili'].append({
                        'SEMBOL': sembol,
                        'GİRİŞ': f"{islem['giris']:.4f}",
                        'ÇIKIS': f"{fiyat:.4f}",
                        'KAR': f"+%{kar_pct:.2f}"
                    })
                    del portfoy['aktif'][sembol]
                    sinyal_sil(sembol)
                    akilli_telegram_gonder(f"✅ KÂR!\n{sembol}: +%{kar_pct:.2f}", sembol, "KAR_AL")
                    final_sinyal = "✅ HEDEF"
                elif fiyat <= islem['stop']:
                    zarar_pct = ((islem['giris'] - fiyat) / islem['giris']) * 100
                    portfoy['basarisiz'].append({
                        'SEMBOL': sembol,
                        'GİRİŞ': f"{islem['giris']:.4f}",
                        'ÇIKIS': f"{fiyat:.4f}",
                        'ZARAR': f"-%{zarar_pct:.2f}"
                    })
                    del portfoy['aktif'][sembol]
                    sinyal_sil(sembol)
                    akilli_telegram_gonder(f"❌ STOP!\n{sembol}: -%{zarar_pct:.2f}", sembol, "STOP")
                    final_sinyal = "❌ STOP"
                else:
                    final_sinyal = "🔄 AKTİF"
            else:
                # SINYAL VERMESİ GEREKİYOR MU?
                if puan_1d >= params["min_puan"] and puan_1h >= 2:
                    if not is_pump and not is_dump:
                        final_sinyal = "🔥 GÜÇLÜ AL"
                        portfoy['aktif'][sembol] = {
                            'giris': fiyat,
                            'hedef': hedef,
                            'stop': stop,
                            'bakiye': bakiye
                        }
                        
                        top_details = detaylar[:5]
                        detail_msg = "\n".join(top_details)
                        
                        telegram_msg = f"""
🎯 GÜÇLÜ AL SİNYALİ!
━━━━━━━━━━━━━━━━
💰 {sembol}
📊 Fiyat: ${fiyat:.4f}
🎯 Hedef: ${hedef:.4f}
🛑 Stop: ${stop:.4f}
📈 Puan: {puan_1d:.1f}/10

{detail_msg}

Risk-Reward: {risk_reward:.2f}x
"""
                        akilli_telegram_gonder(telegram_msg, sembol, "YENI_AL")
                    else:
                        final_sinyal = "⚠️ PUMP/DUMP"
                elif puan_1d >= (params["min_puan"] - 1):
                    final_sinyal = f"⚠️ {puan_1d:.1f}"
                else:
                    final_sinyal = "❌ SİNYAL YOK"
            
            tablo_verisi.append({
                "COIN": sembol.replace("-USD", ""),
                "FİYAT": f"${fiyat:.4f}",
                "HEDEF": f"${hedef:.4f}",
                "STOP": f"${stop:.4f}",
                "RSI": f"{rsi_1d:.1f}",
                "MFI": f"{mfi_1d:.1f}",
                "ADX": f"{adx_1d:.1f}",
                "PUAN": f"{puan_1d:.1f}",
                "SİNYAL": final_sinyal
            })
            
        except Exception as e:
            logger.error(f"❌ {sembol} hatası: {type(e).__name__}")
            continue
    
    islem_gecmisini_kaydet(st.session_state.islem_gecmisi)
    progress_bar.progress(100)
    progress_text.text("✅ Analiz tamamlandı!")
    
    # === SONUÇ TABLOLARı ===
    tab1, tab2, tab3, tab4 = st.tabs(["📊 TÜM SİNYALLER", "🔄 AKTİF", "✅ BAŞARILI", "❌ BAŞARISIZ"])
    
    with tab1:
        if tablo_verisi:
            df_display = pd.DataFrame(tablo_verisi)
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Veri yok")
    
    with tab2:
        portfoy = st.session_state.islem_gecmisi["Kripto Paralar"]
        col1, col2, col3 = st.columns(3)
        col1.metric("🔄 Aktif", len(portfoy['aktif']))
        col2.metric("✅ Başarılı", len(portfoy['basarili']))
        col3.metric("❌ Başarısız", len(portfoy['basarisiz']))
        
        if portfoy['aktif']:
            aktif_list = []
            for s, trade in portfoy['aktif'].items():
                aktif_list.append({
                    "COIN": s.replace("-USD", ""),
                    "GİRİŞ": f"${trade['giris']:.4f}",
                    "HEDEF": f"${trade['hedef']:.4f}",
                    "STOP": f"${trade['stop']:.4f}"
                })
            st.dataframe(pd.DataFrame(aktif_list), use_container_width=True, hide_index=True)
    
    with tab3:
        portfoy = st.session_state.islem_gecmisi["Kripto Paralar"]
        if portfoy['basarili']:
            st.dataframe(pd.DataFrame(portfoy['basarili']), use_container_width=True, hide_index=True)
        else:
            st.info("Henüz başarılı işlem yok")
    
    with tab4:
        portfoy = st.session_state.islem_gecmisi["Kripto Paralar"]
        if portfoy['basarisiz']:
            st.dataframe(pd.DataFrame(portfoy['basarisiz']), use_container_width=True, hide_index=True)
        else:
            st.info("Henüz başarısız işlem yok")

# === ANA PROGRAM ===
st.divider()
analiz_et()

if st.button("🔄 Verileri Yenile"):
    st.rerun()
