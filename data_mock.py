import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_mock_data(n_bars=10000, start_date='2020-01-01'):
    """Генерирует DataFrame с колонками: time, open, high, low, close, volume"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    times = [start + timedelta(minutes=i) for i in range(n_bars)]
    
    # Случайное блуждание (random walk) для цены
    price = 10000
    opens = []
    highs = []
    lows = []
    closes = []
    
    for _ in range(n_bars):
        change = np.random.normal(0, 50)  # волатильность 50 пунктов
        open_price = price
        close_price = price + change
        high_price = max(open_price, close_price) + abs(np.random.normal(0, 20))
        low_price = min(open_price, close_price) - abs(np.random.normal(0, 20))
        
        opens.append(open_price)
        highs.append(high_price)
        lows.append(low_price)
        closes.append(close_price)
        price = close_price  # следующая свеча начинается с цены закрытия
    
    volumes = np.random.randint(100, 10000, n_bars)
    
    return pd.DataFrame({
        'time': times,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })