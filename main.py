import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QSlider, QLabel, QMessageBox,
                             QFrame, QSplitter)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QFont
import pandas as pd

from data_fetcher import BinanceFetcher
from data_aggregator import DataAggregator
from chart_widget import ChartWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Демо-терминал - TradingView Clone")
        self.setGeometry(100, 100, 1600, 900)
        
        # Инициализация
        self.fetcher = BinanceFetcher('data')
        self.data_cache = {}
        self.current_symbol = 'BTCUSDT'
        self.current_tf = '1H'
        self.aggregator = None
        self.current_data = None
        self.current_index = 0
        self.current_position_ms = None
        self.full_data = None
        
        # Демо-торговля
        self.balance = 10000.0
        self.position = 0
        self.entry_price = 0.0
        self.trades = []
        
        # Настройки воспроизведения
        self.play_speed = 1.0
        self.is_playing = False
        self.is_paused = False
        
        # Создаем интерфейс
        self.setup_ui()
        
        # Загружаем данные
        self.load_data(self.current_symbol)
        
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(3)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # --- Верхняя панель ---
        top_panel = QHBoxLayout()
        top_panel.setSpacing(10)
        
        # Заголовок
        title = QLabel("📊 Демо-терминал")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        top_panel.addWidget(title)
        
        top_panel.addWidget(QLabel("|"))
        
        # Выбор актива
        top_panel.addWidget(QLabel("Актив:"))
        self.asset_combo = QComboBox()
        self.asset_combo.addItems(['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'])
        self.asset_combo.setFixedWidth(100)
        self.asset_combo.currentTextChanged.connect(self.on_asset_changed)
        top_panel.addWidget(self.asset_combo)
        
        # Выбор ТФ
        top_panel.addWidget(QLabel("ТФ:"))
        self.tf_combo = QComboBox()
        self.tf_combo.addItems(['1m', '5m', '15m', '1H', '4H', '1D', '1W'])
        self.tf_combo.setCurrentText('1H')
        self.tf_combo.setFixedWidth(60)
        self.tf_combo.currentTextChanged.connect(self.on_tf_changed)
        top_panel.addWidget(self.tf_combo)
        
        top_panel.addWidget(QLabel("|"))
        
        # Кнопка обновить
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedSize(30, 30)
        self.btn_refresh.setToolTip("Обновить данные")
        self.btn_refresh.clicked.connect(self.on_refresh)
        top_panel.addWidget(self.btn_refresh)
        
        top_panel.addStretch()
        
        # Информация о данных
        self.data_info_label = QLabel("Свечей: 0 | Период: -")
        self.data_info_label.setFont(QFont("Arial", 9))
        top_panel.addWidget(self.data_info_label)
        
        top_panel.addWidget(QLabel("|"))
        
        # Баланс
        self.balance_label = QLabel("💰 $10,000.00")
        self.balance_label.setFont(QFont("Arial", 10, QFont.Bold))
        top_panel.addWidget(self.balance_label)
        
        top_panel.addWidget(QLabel("|"))
        
        # PnL
        self.pnl_label = QLabel("PnL: $0.00")
        self.pnl_label.setFont(QFont("Arial", 10))
        top_panel.addWidget(self.pnl_label)
        
        main_layout.addLayout(top_panel)
        
        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # --- График ---
        self.chart = ChartWidget()
        main_layout.addWidget(self.chart, stretch=10)
        
        # --- Нижняя панель ---
        bottom_panel = QVBoxLayout()
        bottom_panel.setSpacing(5)
        
        # Слайдер времени
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("⏱️"))
        
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(1000)
        self.time_slider.setTickPosition(QSlider.TicksBelow)
        self.time_slider.setTickInterval(100)
        self.time_slider.valueChanged.connect(self.on_slider_changed)
        slider_layout.addWidget(self.time_slider)
        
        self.time_label = QLabel("2020-01-01 00:00")
        self.time_label.setFont(QFont("Arial", 9))
        self.time_label.setFixedWidth(150)
        slider_layout.addWidget(self.time_label)
        
        self.position_label = QLabel("0 / 0")
        self.position_label.setFont(QFont("Arial", 9))
        self.position_label.setFixedWidth(80)
        slider_layout.addWidget(self.position_label)
        
        bottom_panel.addLayout(slider_layout)
        
        # Кнопки управления
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        # Кнопки навигации
        self.btn_begin = QPushButton("⏮")
        self.btn_begin.setFixedSize(35, 30)
        self.btn_begin.setToolTip("В начало")
        self.btn_begin.clicked.connect(self.go_to_begin)
        btn_layout.addWidget(self.btn_begin)
        
        self.btn_step_back = QPushButton("⏪")
        self.btn_step_back.setFixedSize(35, 30)
        self.btn_step_back.setToolTip("Шаг назад")
        self.btn_step_back.clicked.connect(self.on_step_back)
        btn_layout.addWidget(self.btn_step_back)
        
        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setFixedSize(80, 30)
        self.btn_play.setToolTip("Воспроизвести историю")
        self.btn_play.clicked.connect(self.on_play)
        btn_layout.addWidget(self.btn_play)
        
        self.btn_step_forward = QPushButton("⏩")
        self.btn_step_forward.setFixedSize(35, 30)
        self.btn_step_forward.setToolTip("Шаг вперед")
        self.btn_step_forward.clicked.connect(self.on_step_forward)
        btn_layout.addWidget(self.btn_step_forward)
        
        self.btn_end = QPushButton("⏭")
        self.btn_end.setFixedSize(35, 30)
        self.btn_end.setToolTip("В конец")
        self.btn_end.clicked.connect(self.go_to_end)
        btn_layout.addWidget(self.btn_end)
        
        btn_layout.addWidget(QLabel("|"))
        
        # Скорость
        btn_layout.addWidget(QLabel("Скорость:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(['0.1x', '0.25x', '0.5x', '1x', '2x', '5x', '10x'])
        self.speed_combo.setCurrentText('1x')
        self.speed_combo.setFixedWidth(60)
        self.speed_combo.currentTextChanged.connect(self.on_speed_changed)
        btn_layout.addWidget(self.speed_combo)
        
        btn_layout.addStretch()
        
        # Статус
        self.status_label = QLabel("✅ Готов")
        self.status_label.setFont(QFont("Arial", 9))
        btn_layout.addWidget(self.status_label)
        
        bottom_panel.addLayout(btn_layout)
        main_layout.addLayout(bottom_panel)
        
        # --- Таймер ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.play_step)
        
    def get_speed_ms(self) -> int:
        speed_text = self.speed_combo.currentText()
        speed = float(speed_text.replace('x', ''))
        base_ms = 100
        return int(base_ms / speed)
    
    def load_data(self, symbol: str, force_refresh: bool = False):
        self.status_label.setText(f"⏳ Загрузка {symbol}...")
        self.btn_refresh.setEnabled(False)
        
        try:
            if symbol not in self.data_cache or force_refresh:
                df = self.fetcher.fetch_with_cache(
                    symbol=symbol,
                    interval='1m',
                    years=3,
                    force_refresh=force_refresh
                )
                
                if df.empty:
                    QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить данные для {symbol}")
                    return
                
                self.aggregator = DataAggregator(df)
                self.data_cache[symbol] = self.aggregator
            else:
                self.aggregator = self.data_cache[symbol]
            
            self.full_data = self.aggregator.aggregate(self.current_tf)
            
            if self.full_data.empty:
                QMessageBox.warning(self, "Ошибка", f"Нет данных для {self.current_tf}")
                return
            
            # --- ИСПРАВЛЕНИЕ: Показываем последние 300 свечей при старте ---
            total_bars = len(self.full_data)
            if total_bars > 300:
                self.current_index = total_bars - 300
            else:
                self.current_index = 0
            
            self.current_position_ms = None
            
            self.update_slider()
            self.update_chart()
            self.update_info()
            
            self.status_label.setText(f"✅ {symbol} {self.current_tf} - {total_bars} свечей")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных: {e}")
            self.status_label.setText("❌ Ошибка загрузки")
        finally:
            self.btn_refresh.setEnabled(True)
    
    def get_trimmed_data(self):
        if self.full_data is None or self.full_data.empty:
            return pd.DataFrame()
        
        if self.current_index >= len(self.full_data):
            self.current_index = len(self.full_data) - 1
        
        trimmed = self.full_data.iloc[:self.current_index + 1].copy()
        return trimmed
    
    def update_chart(self):
        trimmed = self.get_trimmed_data()
        if trimmed.empty:
            return
        
        self.chart.set_data(trimmed)
        
        if len(trimmed) > 0:
            self.chart.show_last_bars(300)
    
    def update_slider(self):
        if self.full_data is not None and not self.full_data.empty:
            max_val = len(self.full_data) - 1
            self.time_slider.setMaximum(max(0, max_val))
            self.time_slider.setValue(min(self.current_index, max_val))
            self.update_time_label()
    
    def update_time_label(self):
        if self.full_data is not None and not self.full_data.empty:
            max_idx = len(self.full_data) - 1
            idx = min(self.current_index, max_idx)
            
            dt = self.full_data.iloc[idx]['time']
            self.time_label.setText(dt.strftime('%Y-%m-%d %H:%M'))
            self.position_label.setText(f"{idx + 1} / {max_idx + 1}")
    
    def update_info(self):
        if self.full_data is not None and not self.full_data.empty:
            start = self.full_data.iloc[0]['time'].strftime('%Y-%m-%d')
            end = self.full_data.iloc[-1]['time'].strftime('%Y-%m-%d')
            self.data_info_label.setText(f"Свечей: {len(self.full_data)} | {start} → {end}")
    
    def update_balance_display(self):
        pnl = self.balance - 10000
        color = "green" if pnl >= 0 else "red"
        
        self.balance_label.setText(f"💰 ${self.balance:,.2f}")
        self.pnl_label.setText(f'PnL: <span style="color:{color}">${pnl:,.2f}</span>')
        self.pnl_label.setTextFormat(Qt.RichText)
    
    def go_to_begin(self):
        if self.is_playing:
            self.on_stop()
        self.current_index = 0
        self.time_slider.setValue(0)
        self.update_chart()
        self.update_time_label()
    
    def go_to_end(self):
        if self.is_playing:
            self.on_stop()
        if self.full_data is not None and not self.full_data.empty:
            self.current_index = len(self.full_data) - 1
            self.time_slider.setValue(self.current_index)
            self.update_chart()
            self.update_time_label()
    
    def on_asset_changed(self, symbol):
        if symbol != self.current_symbol:
            self.current_symbol = symbol
            self.current_position_ms = None
            self.current_index = 0
            self.load_data(symbol)
    
    def on_tf_changed(self, tf):
        if tf != self.current_tf:
            if self.full_data is not None and not self.full_data.empty:
                idx = min(self.current_index, len(self.full_data) - 1)
                dt = self.full_data.iloc[idx]['time']
                self.current_position_ms = int(dt.timestamp() * 1000)
            
            self.current_tf = tf
            
            if self.aggregator is not None:
                self.full_data = self.aggregator.aggregate(tf)
                
                if self.full_data.empty:
                    QMessageBox.warning(self, "Предупреждение", f"Нет данных для {tf}")
                    self.tf_combo.setCurrentText(self.current_tf)
                    return
                
                if self.current_position_ms is not None:
                    self.current_index = self.find_nearest_index(self.current_position_ms)
                else:
                    # По умолчанию показываем последние 300
                    total_bars = len(self.full_data)
                    self.current_index = max(0, total_bars - 300)
                
                self.update_slider()
                self.update_chart()
                self.update_info()
                self.status_label.setText(f"✅ {self.current_symbol} {tf} - {len(self.full_data)} свечей")
    
    def find_nearest_index(self, timestamp_ms: int) -> int:
        if self.full_data is None or self.full_data.empty:
            return 0
        
        times_ms = self.full_data['time'].apply(lambda x: int(x.timestamp() * 1000))
        idx = (times_ms - timestamp_ms).abs().idxmin()
        return int(idx)
    
    def on_speed_changed(self, speed_text):
        if self.is_playing:
            self.timer.stop()
            self.timer.start(self.get_speed_ms())
    
    def on_refresh(self):
        self.load_data(self.current_symbol, force_refresh=True)
    
    def on_slider_changed(self, value):
        if self.full_data is None or self.full_data.empty:
            return
        
        self.current_index = min(value, len(self.full_data) - 1)
        self.update_time_label()
        self.update_chart()
    
    def on_play(self):
        if self.full_data is None or self.full_data.empty:
            return
        
        if self.current_index >= len(self.full_data) - 1:
            self.current_index = max(0, len(self.full_data) - 301)
            self.time_slider.setValue(self.current_index)
            self.update_chart()
        
        if self.is_playing:
            self.is_playing = False
            self.timer.stop()
            self.btn_play.setText("▶ Play")
            self.status_label.setText("⏸ Пауза")
        else:
            self.is_playing = True
            self.btn_play.setText("⏸ Пауза")
            self.timer.start(self.get_speed_ms())
            self.status_label.setText("▶ Воспроизведение...")
    
    def on_stop(self):
        self.is_playing = False
        self.timer.stop()
        self.btn_play.setText("▶ Play")
        self.status_label.setText("⏹ Остановлен")
    
    def on_step_back(self):
        if self.is_playing:
            return
        
        if self.full_data is not None and self.current_index > 0:
            self.current_index -= 1
            self.time_slider.setValue(self.current_index)
            self.update_chart()
            self.update_time_label()
    
    def on_step_forward(self):
        if self.is_playing:
            return
        
        if self.full_data is not None and self.current_index < len(self.full_data) - 1:
            self.current_index += 1
            self.time_slider.setValue(self.current_index)
            self.update_chart()
            self.update_time_label()
    
    def play_step(self):
        if self.full_data is None or self.full_data.empty:
            self.on_stop()
            return
        
        if self.current_index >= len(self.full_data) - 1:
            self.on_stop()
            self.status_label.setText("✅ История закончилась")
            self.btn_play.setText("▶ Play")
            return
        
        self.current_index += 1
        self.time_slider.setValue(self.current_index)
    
    def closeEvent(self, event):
        self.on_stop()
        event.accept()

def main():
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()