import os
import time
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional, List

class BinanceFetcher:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.base_url = 'https://api.binance.com/api/v3/klines'
        
    def fetch_klines(self, symbol: str, interval: str = '1m', 
                     start_str: Optional[str] = None, 
                     end_str: Optional[str] = None,
                     limit: int = 1000) -> pd.DataFrame:
        """
        Скачивает свечи с Binance
        
        Args:
            symbol: 'BTCUSDT', 'ETHUSDT' и т.д.
            interval: '1m', '5m', '1h', '1d' и т.д.
            start_str: '1 Jan 2023' или '2023-01-01'
            end_str: '31 Dec 2023'
            limit: максимум за один запрос (1000)
        
        Returns:
            DataFrame с колонками: time, open, high, low, close, volume
        """
        all_klines = []
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        if start_str:
            params['startTime'] = int(datetime.strptime(start_str, '%Y-%m-%d').timestamp() * 1000)
        if end_str:
            params['endTime'] = int(datetime.strptime(end_str, '%Y-%m-%d').timestamp() * 1000)
        
        while True:
            try:
                response = requests.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    break
                
                all_klines.extend(data)
                
                # Если получили меньше limit, значит данных больше нет
                if len(data) < limit:
                    break
                
                # Сдвигаем startTime на последнюю свечу + 1 мс
                last_time = data[-1][0] + 1
                params['startTime'] = last_time
                
                # Защита от бесконечного цикла
                time.sleep(0.1)  # Пауза, чтобы не забанили
                
            except requests.exceptions.RequestException as e:
                print(f"Ошибка при запросе: {e}")
                break
        
        if not all_klines:
            return pd.DataFrame()
        
        # Преобразуем в DataFrame
        df = pd.DataFrame(all_klines, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Оставляем только нужные колонки
        df = df[['time', 'open', 'high', 'low', 'close', 'volume']].copy()
        
        # Конвертируем типы
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        return df
    
    def fetch_with_cache(self, symbol: str, interval: str = '1m', 
                         years: int = 3, force_refresh: bool = False) -> pd.DataFrame:
        """
        Скачивает данные с кешированием в Parquet
        
        Args:
            symbol: 'BTCUSDT'
            interval: '1m'
            years: сколько лет истории скачать
            force_refresh: принудительно перескачать
        """
        # Имя файла: BTCUSDT_1m_3years.parquet
        filename = f"{symbol}_{interval}_{years}years.parquet"
        filepath = os.path.join(self.data_dir, filename)
        
        # Проверяем кеш
        if not force_refresh and os.path.exists(filepath):
            print(f"Загружаем из кеша: {filepath}")
            return pd.read_parquet(filepath)
        
        print(f"Скачиваем данные для {symbol} за {years} лет...")
        
        # Скачиваем по частям (Binance лимит 1000 свечей за запрос)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)
        
        # Скачиваем с Binance (у них есть публичные CSV архивы, но API проще)
        df = self.fetch_klines(
            symbol=symbol,
            interval=interval,
            start_str=start_date.strftime('%Y-%m-%d'),
            end_str=end_date.strftime('%Y-%m-%d')
        )
        
        if df.empty:
            print(f"Не удалось скачать данные для {symbol}")
            return df
        
        # Сохраняем в Parquet (сжатый, быстрый)
        df.to_parquet(filepath, compression='snappy')
        print(f"Сохранено {len(df)} свечей в {filepath}")
        
        return df
    
    def fetch_multiple(self, symbols: List[str], interval: str = '1m', 
                       years: int = 3) -> dict:
        """Скачивает данные для нескольких активов"""
        result = {}
        for symbol in symbols:
            df = self.fetch_with_cache(symbol, interval, years)
            if not df.empty:
                result[symbol] = df
        return result