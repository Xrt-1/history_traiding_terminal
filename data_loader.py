import os
import pandas as pd
from datetime import datetime, timedelta
import glob
import re

class DataLoader:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
    def parse_filename(self, filename: str) -> dict:
        pattern = r'(.+)-(.+)-(\d{4})-(\d{2})\.csv'
        match = re.match(pattern, filename)
        if match:
            return {
                'symbol': match.group(1),
                'interval': match.group(2),
                'year': int(match.group(3)),
                'month': int(match.group(4))
            }
        return None
    
    def check_time_continuity(self, files: list, symbol: str, interval: str = '1m') -> tuple:
        months = []
        for file in files:
            parsed = self.parse_filename(os.path.basename(file))
            if parsed and parsed['symbol'] == symbol and parsed['interval'] == interval:
                months.append((parsed['year'], parsed['month']))
        
        if not months:
            return False, [], []
        
        months = sorted(months)
        first_year, first_month = months[0]
        last_year, last_month = months[-1]
        loaded_set = set(months)
        
        expected_months = []
        current_year, current_month = first_year, first_month
        
        while (current_year < last_year) or (current_year == last_year and current_month <= last_month):
            expected_months.append((current_year, current_month))
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
        
        missing = [m for m in expected_months if m not in loaded_set]
        return len(missing) == 0, missing, months
    
    def convert_timestamp(self, ts: int) -> int:
        ts_str = str(int(ts))
        num_digits = len(ts_str)
        
        if num_digits <= 10:
            return ts * 1000
        elif num_digits <= 13:
            return ts
        elif num_digits <= 16:
            return ts // 1000
        else:
            return ts // 1000000
    
    def load_csv_files(self, symbol: str, interval: str = '1m', 
                   check_continuity: bool = True, 
                   auto_fix: bool = False) -> pd.DataFrame:
        pattern = os.path.join(self.data_dir, f"{symbol}-{interval}-*.csv")
        files = glob.glob(pattern)
        
        if not files:
            print(f"❌ Файлы не найдены: {pattern}")
            return pd.DataFrame()
        
        print(f"📁 Найдено {len(files)} файлов для {symbol}")
        
        if check_continuity:
            is_continuous, missing, loaded_months = self.check_time_continuity(files, symbol, interval)
            if not is_continuous:
                print(f"⚠️ ВНИМАНИЕ: Обнаружены пропуски в данных!")
                print(f"   Загружено месяцев: {len(loaded_months)}")
                print(f"   Пропущено месяцев: {len(missing)}")
                if missing:
                    print(f"   Пропущенные месяцы: {missing[:10]}{'...' if len(missing) > 10 else ''}")
            else:
                print(f"✅ Непрерывность подтверждена")
        
        all_data = []
        total_files = len(files)
        
        for i, file in enumerate(sorted(files), 1):
            print(f"   [{i}/{total_files}] {os.path.basename(file)}...", end=' ')
            try:
                df = pd.read_csv(
                    file,
                    header=None,
                    names=['open_time', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_volume', 'trades', 
                        'taker_buy_base', 'taker_buy_quote', 'ignore'],
                    dtype={'open_time': 'float64', 'open': 'float64', 
                        'high': 'float64', 'low': 'float64', 
                        'close': 'float64', 'volume': 'float64'}
                )
                all_data.append(df)
                print(f"✅ {len(df)} свечей")
            except Exception as e:
                print(f"⚠️ Ошибка: {e}")
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.concat(all_data, ignore_index=True)
        
        # Конвертация времени
        df['open_time'] = pd.to_numeric(df['open_time'], errors='coerce')
        df = df.dropna(subset=['open_time'])
        
        if df.empty:
            print("❌ Нет корректных временных меток")
            return pd.DataFrame()
        
        times = df['open_time'].astype('int64')
        converted_times = times.apply(self.convert_timestamp)
        
        # Проверка диапазона
        min_valid_ms = 1262304000000
        max_valid_ms = 2051222400000
        mask = (converted_times >= min_valid_ms) & (converted_times <= max_valid_ms)
        
        invalid_count = (~mask).sum()
        if invalid_count > 0:
            print(f"⚠️ Пропущено {invalid_count} некорректных временных меток")
        
        df = df[mask].copy()
        converted_times = converted_times[mask]
        
        if df.empty:
            print("❌ Все временные метки некорректны")
            return pd.DataFrame()
        
        df['time'] = pd.to_datetime(converted_times, unit='ms')
        df = df[['time', 'open', 'high', 'low', 'close', 'volume']].copy()
        df = df.sort_values('time').reset_index(drop=True)
        
        print(f"✅ Загружено {len(df)} свечей")
        print(f"   Период: {df['time'].min()} -> {df['time'].max()}")
        
        return df
    
    def check_data_gaps(self, df: pd.DataFrame, symbol: str, max_gap_minutes: int = 10):
        if df.empty or len(df) < 2:
            return
        
        time_diff = df['time'].diff().dt.total_seconds() / 60
        large_gaps = time_diff[time_diff > 60]
        
        if not large_gaps.empty:
            print(f"   ⚠️ Обнаружено {len(large_gaps)} разрывов в данных:")
            for idx in large_gaps.index[:5]:
                gap_minutes = large_gaps[idx]
                prev_time = df.iloc[idx-1]['time']
                curr_time = df.iloc[idx]['time']
                print(f"      Разрыв {gap_minutes:.0f} минут между {prev_time} и {curr_time}")
    
    def get_missing_months(self, symbol: str, interval: str = '1m', 
                           start_year: int = 2020, end_year: int = None) -> list:
        if end_year is None:
            end_year = datetime.now().year
        
        pattern = os.path.join(self.data_dir, f"{symbol}-{interval}-*.csv")
        files = glob.glob(pattern)
        
        existing = []
        for file in files:
            parsed = self.parse_filename(os.path.basename(file))
            if parsed:
                existing.append((parsed['year'], parsed['month']))
        
        expected = []
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                if year == end_year and month > datetime.now().month:
                    break
                expected.append((year, month))
        
        missing = [m for m in expected if m not in existing]
        return missing
    
    def save_to_parquet(self, df: pd.DataFrame, symbol: str, interval: str = '1m'):
        if df.empty:
            return
        
        filename = f"{symbol}_{interval}.parquet"
        filepath = os.path.join(self.data_dir, filename)
        df.to_parquet(filepath, compression='snappy')
        print(f"💾 Сохранено в {filepath}")
        
    def load_from_parquet(self, symbol: str, interval: str = '1m') -> pd.DataFrame:
        filename = f"{symbol}_{interval}.parquet"
        filepath = os.path.join(self.data_dir, filename)
        
        if os.path.exists(filepath):
            print(f"📂 Загрузка из кеша: {filename}")
            return pd.read_parquet(filepath)
        return pd.DataFrame()