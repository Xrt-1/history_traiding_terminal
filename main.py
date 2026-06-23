import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QSlider, QLabel, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
import pandas as pd

from data_fetcher import BinanceFetcher
from data_aggregator import DataAggregator
from chart_widget import ChartWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Демо-терминал")
        self.setGeometry(100, 100, 1400, 800)
        
        # Инициализация
        self.fetcher = BinanceFetcher('data')
        self.data_cache = {}  # Словарь {symbol: DataAggregator}
        self.current_symbol = 'BTCUSDT'
        self.current_tf = '1H'
        self.aggregator = None
        self.current_data = None
        self.current_position = None
        self.current_index = 0
        
        # Демо-торговля
        self.balance = 10000.0
        self.position = 0  # 0 - нет позиции, 1 - LONG, -1 - SHORT
        self.entry_price = 0.0
        self.trades = []
        
        # Создаем интерфейс
        self.setup_ui()
        
        # Загружаем данные для первого актива
        self.load_data(self.current_symbol)
        
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(5)
        
        # --- Верхняя панель ---
        top_panel = QHBoxLayout()
        
        # Выбор актива
        self.asset_combo = QComboBox()
        self.asset_combo.addItems(['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'])
        self.asset_combo.currentTextChanged.connect(self.on_asset_changed)
        top_panel.addWidget(QLabel("Актив:"))
        top_panel.addWidget(self.asset_combo)
        
        # Выбор ТФ
        self.tf_combo = QComboBox()
        self.tf_combo.addItems(['1m', '5m', '15m', '1H', '4H', '1D', '1W'])
        self.tf_combo.setCurrentText('1H')
        self.tf_combo.currentTextChanged.connect(self.on_tf_changed)
        top_panel.addWidget(QLabel("ТФ:"))
        top_panel.addWidget(self.tf_combo)
        
        # Кнопка обновить данные
        self.btn_refresh = QPushButton("🔄 Обновить")
        self.btn_refresh.clicked.connect(self.on_refresh)
        top_panel.addWidget(self.btn_refresh)
        
        top_panel.addStretch()
        
        # Инфо о балансе
        self.balance_label = QLabel("Баланс: $10000.00 | PnL: $0.00")
        top_panel.addWidget(self.balance_label)
        
        main_layout.addLayout(top_panel)
        
        # --- График ---
        self.chart = ChartWidget()
        main_layout.addWidget(self.chart, stretch=10)
        
        # --- Нижняя панель ---
        bottom_panel = QVBoxLayout()
        
        # Слайдер времени
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Время:"))
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(1000)
        self.time_slider.valueChanged.connect(self.on_slider_changed)
        slider_layout.addWidget(self.time_slider)
        
        self.time_label = QLabel("2020-01-01 00:00")
        slider_layout.addWidget(self.time_label)
        bottom_panel.addLayout(slider_layout)
        
        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play")
        self.btn_play.clicked.connect(self.on_play)
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_step_back = QPushButton("⏪")
        self.btn_step_back.clicked.connect(self.on_step_back)
        self.btn_step_forward = QPushButton("⏩")
        self.btn_step_forward.clicked.connect(self.on_step_forward)
        
        btn_layout.addWidget(self.btn_play)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_step_back)
        btn_layout.addWidget(self.btn_step_forward)
        btn_layout.addStretch()
        
        self.status_label = QLabel("Статус: Готов")
        btn_layout.addWidget(self.status_label)
        
        bottom_panel.addLayout(btn_layout)
        main_layout.addLayout(bottom_panel)
        
        # --- Таймер для воспроизведения ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.play_step)
        self.is_playing = False
        
    def load_data(self, symbol: str, force_refresh: bool = False):
        """
        Загружает данные для актива
        """
        self.status_label.setText(f"Статус: Загрузка данных для {symbol}...")
        self.btn_refresh.setEnabled(False)
        
        try:
            if symbol not in self.data_cache or force_refresh:
                # Используем быструю загрузку
                df = self.fetcher.fetch_with_cache(
                    symbol=symbol,
                    interval='1m',
                    years=3,  # <-- Параметр years теперь правильно передается
                    force_refresh=force_refresh,
                    use_fast=True  # Используем быструю загрузку
                )
                
                if df.empty:
                    QMessageBox.warning(self, "Ошибка", 
                                    f"Не удалось загрузить данные для {symbol}")
                    return
                
                # Создаем агрегатор
                self.aggregator = DataAggregator(df)
                self.data_cache[symbol] = self.aggregator
            else:
                self.aggregator = self.data_cache[symbol]
            
            # Обновляем текущий ТФ
            self.current_data = self.aggregator.aggregate(self.current_tf)
            
            # Обновляем интерфейс
            self.update_chart()
            self.update_slider()
            
            self.status_label.setText(f"Статус: Загружено {len(self.current_data)} свечей")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных: {e}")
            self.status_label.setText("Статус: Ошибка загрузки")
        finally:
            self.btn_refresh.setEnabled(True)
    def update_chart(self):
        """Обновляет график"""
        if self.current_data is not None and len(self.current_data) > 0:
            self.chart.set_data(self.current_data)
            
            # Восстанавливаем позицию
            if self.current_position is not None:
                self.chart.set_current_time(self.current_position)
            else:
                # Показываем последние 100 свечей
                if len(self.current_data) > 100:
                    last_time = self.current_data.iloc[-1]['time'].timestamp() * 1000
                    self.chart.set_current_time(last_time)
    
    def update_slider(self):
        """Обновляет слайдер"""
        if self.current_data is not None:
            self.time_slider.setMaximum(max(0, len(self.current_data) - 1))
            self.time_slider.setValue(0)
            self.current_index = 0
            self.update_time_label()
    
    def update_time_label(self):
        """Обновляет метку времени"""
        if self.current_data is not None and len(self.current_data) > self.current_index:
            dt = self.current_data.iloc[self.current_index]['time']
            self.time_label.setText(dt.strftime('%Y-%m-%d %H:%M'))
    
    def update_balance(self):
        """Обновляет отображение баланса"""
        pnl = self.balance - 10000
        color = "green" if pnl >= 0 else "red"
        self.balance_label.setText(
            f"Баланс: ${self.balance:.2f} | "
            f'PnL: <span style="color:{color}">${pnl:.2f}</span>'
        )
    
    def on_asset_changed(self, symbol):
        """Переключение актива"""
        if symbol != self.current_symbol:
            self.current_symbol = symbol
            self.current_position = None
            self.load_data(symbol)
    
    def on_tf_changed(self, tf):
        """Переключение ТФ с сохранением позиции"""
        if tf != self.current_tf:
            # Сохраняем текущую позицию
            if self.current_data is not None and len(self.current_data) > self.current_index:
                self.current_position = self.current_data.iloc[self.current_index]['time'].timestamp() * 1000
            
            self.current_tf = tf
            
            if self.aggregator is not None:
                self.current_data = self.aggregator.aggregate(tf)
                self.update_slider()
                self.update_chart()
    
    def on_refresh(self):
        """Принудительное обновление данных"""
        self.load_data(self.current_symbol, force_refresh=True)
    
    def on_slider_changed(self, value):
        """Движение слайдера"""
        self.current_index = value
        self.update_time_label()
        
        if self.current_data is not None and len(self.current_data) > value:
            dt = self.current_data.iloc[value]['time'].timestamp() * 1000
            self.chart.set_current_time(dt)
    
    def on_play(self):
        """Запуск воспроизведения"""
        if self.is_playing:
            self.is_playing = False
            self.timer.stop()
            self.btn_play.setText("▶ Play")
            self.status_label.setText("Статус: Пауза")
            return
        
        if self.current_data is None or len(self.current_data) == 0:
            return
        
        self.is_playing = True
        self.btn_play.setText("⏸ Пауза")
        self.timer.start(50)  # 50 мс на свечу (20 свечей в секунду)
        self.status_label.setText("Статус: Воспроизведение...")
    
    def on_stop(self):
        """Остановка"""
        self.is_playing = False
        self.btn_play.setText("▶ Play")
        self.timer.stop()
        self.status_label.setText("Статус: Остановлен")
    
    def on_step_back(self):
        """Шаг назад"""
        if self.current_data is not None and self.current_index > 0:
            self.current_index -= 1
            self.time_slider.setValue(self.current_index)
            self.process_current_bar()
    
    def on_step_forward(self):
        """Шаг вперед"""
        if self.current_data is not None and self.current_index < len(self.current_data) - 1:
            self.current_index += 1
            self.time_slider.setValue(self.current_index)
            self.process_current_bar()
    
    def play_step(self):
        """Один шаг воспроизведения (Bar-by-Bar)"""
        if self.current_data is None or len(self.current_data) == 0:
            self.on_stop()
            return
        
        if self.current_index >= len(self.current_data) - 1:
            self.on_stop()
            self.status_label.setText("Статус: История закончилась")
            return
        
        self.current_index += 1
        self.time_slider.setValue(self.current_index)
        self.process_current_bar()
    
    def process_current_bar(self):
        """Обработка текущей свечи (стратегия + демо-торговля)"""
        if self.current_data is None or self.current_index >= len(self.current_data):
            return
        
        bar = self.current_data.iloc[self.current_index]
        
        # --- ЗДЕСЬ ВАША СТРАТЕГИЯ ---
        # Пример: простая стратегия на скользящих средних
        # Для демонстрации используем только цену закрытия
        
        price = bar['close']
        
        # Простейшая стратегия: если цена выше 200-периодной средней - покупаем
        # Для этого нужно рассчитать среднюю на истории
        if self.current_index > 200:
            history = self.current_data.iloc[self.current_index-200:self.current_index]
            sma = history['close'].mean()
            
            # Сигнал на покупку
            if price > sma and self.position == 0:
                self.position = 1  # LONG
                self.entry_price = price
                self.trades.append(('BUY', bar['time'], price))
                self.status_label.setText(f"Статус: BUY at ${price:.2f}")
                
            # Сигнал на продажу
            elif price < sma and self.position == 1:
                # Закрываем позицию
                profit = (price - self.entry_price) * 0.1  # 0.1 BTC
                self.balance += profit
                self.position = 0
                self.trades.append(('SELL', bar['time'], price))
                self.status_label.setText(f"Статус: SELL at ${price:.2f}, Profit: ${profit:.2f}")
        
        # Обновляем баланс для отображения
        if self.position == 1:
            current_pnl = (price - self.entry_price) * 0.1
            self.balance_label.setText(
                f"Баланс: ${self.balance:.2f} | "
                f"Позиция: LONG @ ${self.entry_price:.2f} | "
                f"PnL: ${current_pnl:.2f}"
            )
        else:
            self.update_balance()
        
        # Обновляем время
        self.update_time_label()

def main():
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()