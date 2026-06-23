import pandas as pd

class DataAggregator:
    def __init__(self, raw_data: pd.DataFrame):
        self.raw_data = raw_data.copy()
        self.raw_data = self.raw_data.set_index('time')
        self.cache = {}
        
    @staticmethod
    def get_resample_rule(tf: str) -> str:
        tf_map = {
            '1m': '1min',
            '5m': '5min',
            '15m': '15min',
            '1H': '1H',
            '4H': '4H',
            '1D': '1D',
            '1W': '1W'
        }
        return tf_map.get(tf, '1H')
    
    def aggregate(self, tf: str) -> pd.DataFrame:
        if tf in self.cache:
            return self.cache[tf]
        
        rule = self.get_resample_rule(tf)
        
        if self.raw_data.empty:
            return pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        try:
            aggregated = self.raw_data.resample(rule).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            if aggregated.empty:
                return pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            
            aggregated = aggregated.reset_index()
            self.cache[tf] = aggregated
            return aggregated
            
        except Exception as e:
            print(f"❌ Ошибка при агрегации {tf}: {e}")
            return pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    
    def get_available_tfs(self) -> list:
        return ['1m', '5m', '15m', '1H', '4H', '1D', '1W']
    
    def clear_cache(self):
        self.cache.clear()
    
    def get_data_info(self) -> dict:
        if self.raw_data.empty:
            return {'total_bars': 0, 'start_date': None, 'end_date': None}
        
        return {
            'total_bars': len(self.raw_data),
            'start_date': self.raw_data.index.min(),
            'end_date': self.raw_data.index.max()
        }