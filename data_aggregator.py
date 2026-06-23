import pandas as pd
from functools import lru_cache

class DataAggregator:
    def __init__(self, raw_data: pd.DataFrame):
        """
        raw_data: DataFrame с колонками ['time', 'open', 'high', 'low', 'close', 'volume']
                  индексация по времени
        """
        self.raw_data = raw_data.copy()
        self.raw_data = self.raw_data.set_index('time')
        self.cache = {}
        
    @staticmethod
    def get_resample_rule(tf: str) -> str:
        """Преобразует текстовый ТФ в правило pandas"""
        tf_map = {
            '1m': '1T',
            '5m': '5T', 
            '15m': '15T',
            '1H': '1H',
            '4H': '4H',
            '1D': '1D',
            '1W': '1W'
        }
        return tf_map.get(tf, '1H')
    
    def aggregate(self, tf: str) -> pd.DataFrame:
        """
        Возвращает агрегированные данные для указанного ТФ
        Использует кеш для ускорения
        """
        if tf in self.cache:
            return self.cache[tf]
        
        rule = self.get_resample_rule(tf)
        
        # Агрегация
        aggregated = self.raw_data.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # Сбрасываем индекс, чтобы 'time' стала колонкой
        aggregated = aggregated.reset_index()
        
        # Кешируем
        self.cache[tf] = aggregated
        return aggregated
    
    def get_available_tfs(self) -> list:
        """Возвращает список ТФ, для которых есть данные"""
        return ['1m', '5m', '15m', '1H', '4H', '1D', '1W']
    
    def clear_cache(self):
        """Очищает кеш (если данные изменились)"""
        self.cache.clear()