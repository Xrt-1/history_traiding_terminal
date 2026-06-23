import os
import pandas as pd
from data_loader import DataLoader

class BinanceFetcher:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.loader = DataLoader(data_dir)
        os.makedirs(data_dir, exist_ok=True)
        
    def fetch_with_cache(self, symbol: str, interval: str = '1m', 
                         years: int = 3, force_refresh: bool = False) -> pd.DataFrame:
        """
        Загружает данные: сначала пытается из Parquet, потом из CSV, потом через API
        """
        # 1. Пытаемся загрузить из Parquet (кеш)
        if not force_refresh:
            df = self.loader.load_from_parquet(symbol, interval)
            if not df.empty:
                print(f"✅ Загружено {len(df)} свечей из кеша")
                return df
        
        # 2. Пытаемся загрузить из CSV файлов (если вы скачали вручную)
        print(f"📂 Поиск CSV файлов для {symbol}...")
        df = self.loader.load_csv_files(symbol, interval)
        
        if not df.empty:
            # Сохраняем в Parquet для быстрого доступа в следующий раз
            self.loader.save_to_parquet(df, symbol, interval)
            return df
        
        # 3. Если нет ни CSV, ни Parquet - пробуем скачать через API
        #print(f"🌐 CSV файлы не найдены, пробуем скачать через API...")
        #df = self.fetch_from_api(symbol, interval, years)
        
        if not df.empty:
            self.loader.save_to_parquet(df, symbol, interval)
        
        return df
    
    def fetch_from_api(self, symbol: str, interval: str = '1m', years: int = 1) -> pd.DataFrame:
        """
        Скачивает через API (если нет файлов)
        """
        import requests
        import time
        from datetime import datetime, timedelta
        
        print(f"🌐 Скачиваем {symbol} за {years} лет через API...")
        
        all_klines = []
        base_url = 'https://api.binance.com/api/v3/klines'
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)
        start_time = int(start_date.timestamp() * 1000)
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': 1000
        }
        
        total_fetched = 0
        while True:
            params['startTime'] = start_time
            
            try:
                response = requests.get(base_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    break
                
                all_klines.extend(data)
                total_fetched += len(data)
                print(f"   Загружено {total_fetched} свечей...")
                
                if len(data) < 1000:
                    break
                
                start_time = data[-1][0] + 1
                time.sleep(0.1)
                
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                break
        
        if not all_klines:
            return pd.DataFrame()
        
        # Преобразуем в DataFrame
        df = pd.DataFrame(all_klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        
        # --- ИСПРАВЛЕННАЯ КОНВЕРТАЦИЯ ВРЕМЕНИ ---
        # API возвращает миллисекунды (13 цифр), это безопасно
        df['time'] = pd.to_datetime(df['open_time'], unit='ms')
        
        df = df[['time', 'open', 'high', 'low', 'close', 'volume']].copy()
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        print(f"✅ Скачано {len(df)} свечей")
        return df