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
        """
        Парсит имя файла вида: BTCUSDT-1m-2024-01.csv
        Возвращает: {'symbol': 'BTCUSDT', 'interval': '1m', 'year': 2024, 'month': 1}
        """
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
        """
        Проверяет непрерывность временного ряда по именам файлов
        
        Returns:
            (is_continuous, missing_months, loaded_months)
            is_continuous: True если все месяцы подряд без пропусков
            missing_months: список пропущенных месяцев [(year, month), ...]
            loaded_months: список загруженных месяцев [(year, month), ...]
        """
        months = []
        for file in files:
            parsed = self.parse_filename(os.path.basename(file))
            if parsed and parsed['symbol'] == symbol and parsed['interval'] == interval:
                months.append((parsed['year'], parsed['month']))
        
        if not months:
            return False, [], []
        
        # Сортируем по дате
        months = sorted(months)
        
        # Определяем ожидаемый диапазон
        first_year, first_month = months[0]
        last_year, last_month = months[-1]
        
        # Создаем множество загруженных месяцев для быстрой проверки
        loaded_set = set(months)
        
        # Генерируем все ожидаемые месяцы
        expected_months = []
        current_year, current_month = first_year, first_month
        
        while (current_year < last_year) or (current_year == last_year and current_month <= last_month):
            expected_months.append((current_year, current_month))
            
            # Переход на следующий месяц
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
        
        # Ищем пропуски
        missing = [m for m in expected_months if m not in loaded_set]
        
        return len(missing) == 0, missing, months
    
    def convert_timestamp(self, ts: int) -> int:
        """
        Конвертирует временную метку в миллисекунды.
        Определяет формат по количеству цифр:
        - 10 цифр: секунды -> умножаем на 1000
        - 13 цифр: миллисекунды -> оставляем как есть
        - 16 цифр: микросекунды -> делим на 1000
        - 19 цифр: наносекунды -> делим на 1000000
        """
        ts_str = str(int(ts))
        num_digits = len(ts_str)
        
        if num_digits <= 10:
            # Секунды (например, 1502942400)
            return ts * 1000
        elif num_digits <= 13:
            # Миллисекунды (например, 1506816000000)
            return ts
        elif num_digits <= 16:
            # Микросекунды (например, 1740787200000000)
            return ts // 1000
        else:
            # Наносекунды (например, 1740787200000000000)
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
        for file in sorted(files):
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
            except Exception as e:
                print(f"   ⚠️ Ошибка в файле {file}: {e}")
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.concat(all_data, ignore_index=True)
        
        # --- КОНВЕРТАЦИЯ ВРЕМЕНИ С ПОДДЕРЖКОЙ СМЕШАННЫХ ФОРМАТОВ ---
        # Убедимся, что данные числовые
        df['open_time'] = pd.to_numeric(df['open_time'], errors='coerce')
        df = df.dropna(subset=['open_time'])
        
        if df.empty:
            print("❌ Нет корректных временных меток")
            return pd.DataFrame()
        
        # Конвертируем в int64
        times = df['open_time'].astype('int64')
        
        # Конвертируем каждую временную метку в миллисекунды
        print("🔄 Конвертируем временные метки в миллисекунды...")
        
        # Применяем конвертацию к каждому значению
        converted_times = times.apply(self.convert_timestamp)
        
        # Проверяем, что все значения сконвертированы корректно
        # Допустимый диапазон: 2010-2035 годы в миллисекундах
        min_valid_ms = 1262304000000  # 2010-01-01
        max_valid_ms = 2051222400000  # 2035-01-01
        
        # Проверяем, что значения в допустимом диапазоне
        mask = (converted_times >= min_valid_ms) & (converted_times <= max_valid_ms)
        
        invalid_count = (~mask).sum()
        if invalid_count > 0:
            print(f"⚠️ Найдены некорректные временные метки. Пропускаем {invalid_count} записей")
            
            # Показываем примеры некорректных значений
            invalid_indices = ~mask
            invalid_original = times[invalid_indices]
            invalid_converted = converted_times[invalid_indices]
            
            if len(invalid_original) > 0:
                print(f"   Примеры некорректных временных меток (оригинал -> конвертировано):")
                for i in range(min(5, len(invalid_original))):
                    orig = invalid_original.iloc[i]
                    conv = invalid_converted.iloc[i]
                    try:
                        dt = pd.to_datetime(conv, unit='ms')
                        print(f"      {orig} -> {conv} -> {dt}")
                    except:
                        print(f"      {orig} -> {conv} -> невозможно преобразовать")
                
                # Показываем статистику
                print(f"   Статистика по некорректным значениям:")
                print(f"      Минимальное исходное: {invalid_original.min()}")
                print(f"      Максимальное исходное: {invalid_original.max()}")
                print(f"      Минимальное конвертированное: {invalid_converted.min()}")
                print(f"      Максимальное конвертированное: {invalid_converted.max()}")
        
        # Применяем маску
        converted_times = converted_times[mask]
        df = df[mask].copy()
        
        if df.empty:
            print("❌ Все временные метки некорректны")
            return pd.DataFrame()
        
        # Создаем колонку времени
        df['time'] = pd.to_datetime(converted_times, unit='ms')
        
        # Проверяем, не вышли ли за границы pandas (1677-2262)
        min_date = pd.Timestamp('1677-01-01')
        max_date = pd.Timestamp('2262-04-11')
        valid_mask = (df['time'] >= min_date) & (df['time'] <= max_date)
        
        if not valid_mask.all():
            print(f"⚠️ Найдены временные метки вне допустимого диапазона pandas. Пропускаем { (~valid_mask).sum() } записей")
            df = df[valid_mask].copy()
        
        if df.empty:
            print("❌ Нет данных в допустимом временном диапазоне")
            return pd.DataFrame()
        
        # Выбираем нужные колонки
        df = df[['time', 'open', 'high', 'low', 'close', 'volume']].copy()
        df = df.sort_values('time').reset_index(drop=True)
        
        print(f"✅ Загружено {len(df)} свечей")
        print(f"   Период: {df['time'].min()} -> {df['time'].max()}")
        
        return df
        
    def check_data_gaps(self, df: pd.DataFrame, symbol: str, max_gap_minutes: int = 10):
        """
        Проверяет разрывы внутри загруженных данных (по времени)
        """
        if df.empty or len(df) < 2:
            return
        
        # Вычисляем разницу между соседними временными метками
        time_diff = df['time'].diff().dt.total_seconds() / 60
        
        # Находим большие разрывы (больше 60 минут - скорее всего пропуск)
        large_gaps = time_diff[time_diff > 60]
        
        if not large_gaps.empty:
            print(f"   ⚠️ Обнаружено {len(large_gaps)} разрывов в данных:")
            for idx in large_gaps.index[:5]:  # Показываем первые 5
                gap_minutes = large_gaps[idx]
                prev_time = df.iloc[idx-1]['time']
                curr_time = df.iloc[idx]['time']
                print(f"      Разрыв {gap_minutes:.0f} минут между {prev_time} и {curr_time}")
            if len(large_gaps) > 5:
                print(f"      ... и еще {len(large_gaps) - 5} разрывов")
        else:
            # Проверяем что разрывы не больше 10 минут (для 1m данных)
            if max_gap_minutes > 0:
                gaps = time_diff[time_diff > max_gap_minutes]
                if not gaps.empty:
                    print(f"   ⚠️ Найдено {len(gaps)} разрывов > {max_gap_minutes} минут")
    
    def get_missing_months(self, symbol: str, interval: str = '1m', 
                           start_year: int = 2020, end_year: int = None) -> list:
        """
        Показывает какие месяцы отсутствуют в папке
        """
        if end_year is None:
            end_year = datetime.now().year
        
        # Получаем существующие файлы
        pattern = os.path.join(self.data_dir, f"{symbol}-{interval}-*.csv")
        files = glob.glob(pattern)
        
        existing = []
        for file in files:
            parsed = self.parse_filename(os.path.basename(file))
            if parsed:
                existing.append((parsed['year'], parsed['month']))
        
        # Генерируем все ожидаемые месяцы
        expected = []
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                if year == end_year and month > datetime.now().month:
                    break
                expected.append((year, month))
        
        # Находим пропуски
        missing = [m for m in expected if m not in existing]
        return missing
    
    def save_to_parquet(self, df: pd.DataFrame, symbol: str, interval: str = '1m'):
        """Сохраняет в Parquet"""
        if df.empty:
            return
        
        filename = f"{symbol}_{interval}.parquet"
        filepath = os.path.join(self.data_dir, filename)
        df.to_parquet(filepath, compression='snappy')
        print(f"💾 Сохранено в {filepath}")
        
    def load_from_parquet(self, symbol: str, interval: str = '1m') -> pd.DataFrame:
        """Загружает из Parquet"""
        filename = f"{symbol}_{interval}.parquet"
        filepath = os.path.join(self.data_dir, filename)
        
        if os.path.exists(filepath):
            print(f"📂 Загрузка из кеша: {filename}")
            return pd.read_parquet(filepath)
        return pd.DataFrame()