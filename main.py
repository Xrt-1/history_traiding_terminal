import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QSlider, QLabel, QStackedWidget)
from PyQt5.QtCore import Qt, QTimer
import pandas as pd

from data_mock import generate_mock_data
from chart_widget import ChartWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Демо-терминал")
        self.setGeometry(100, 100, 1400, 800)
        
        # Данные
        self.data_raw = generate_mock_data(10000)  # 1-минутные данные
        self.current_tf = '1H'  # Текущий таймфрейм
        self.current_asset = 'BTCUSD'
        self.current_data = None  # Агрегированные данные
        self.current_position = None  # Время на слайдере
        
        # Центральный виджет
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(5)
        
        # --- Верхняя панель ---
        top_panel = QHBoxLayout()
        
        # Выбор актива
        self.asset_combo = QComboBox()
        self.asset_combo.addItems(['BTCUSD', 'ETHUSD', 'SOLUSD'])
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
        
        top_panel.addStretch()
        
        # Инфо о балансе
        self.balance_label = QLabel("Баланс: $10000 | PnL: $0")
        top_panel.addWidget(self.balance_label)
        
        main_layout.addLayout(top_panel)
        
        # --- График ---
        self.chart = ChartWidget()
        main_layout.addWidget(self.chart, stretch=10)
        
        # --- Нижняя панель (слайдер + кнопки) ---
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
        self.btn_step_forward = QPushButton("⏩")
        
        btn_layout.addWidget(self.btn_play)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_step_back)
        btn_layout.addWidget(self.btn_step_forward)
        btn_layout.addStretch()
        
        # Статус торговли
        self.status_label = QLabel("Статус: Ожидание")
        btn_layout.addWidget(self.status_label)
        
        bottom_panel.addLayout(btn_layout)
        main_layout.addLayout(bottom_panel)
        
        # --- Инициализация ---
        self.aggregate_data()
        self.update_chart()
        
        # Таймер для воспроизведения
        self.timer = QTimer()
        self.timer.timeout.connect(self.play_step)
        self.is_playing = False
        self.current_index = 0
        
    def aggregate_data(self):
        """Агрегирует 1-минутные данные в текущий ТФ"""
        if self.data_raw is None or len(self.data_raw) == 0:
            return
            
        # Определяем правило ресемплинга
        tf_map = {
            '1m': '1T', '5m': '5T', '15m': '15T', 
            '1H': '1H', '4H': '4H', '1D': '1D', '1W': '1W'
        }
        rule = tf_map.get(self.current_tf, '1H')
        
        df = self.data_raw.copy()
        df = df.set_index('time')
        
        # Агрегация
        aggregated = df.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        aggregated = aggregated.reset_index()
        self.current_data = aggregated
        
        # Обновляем слайдер
        if len(aggregated) > 0:
            self.time_slider.setMaximum(len(aggregated) - 1)
            self.time_slider.setValue(0)
            self.current_index = 0
            self.update_time_label()
    
    def update_chart(self):
        """Отправляет данные в график"""
        if self.current_data is not None and len(self.current_data) > 0:
            self.chart.set_data(self.current_data)
            # Сохраняем позицию после смены ТФ
            if self.current_position is not None:
                self.chart.set_current_time(self.current_position)
            else:
                # По умолчанию показываем последние 100 свечей
                if len(self.current_data) > 100:
                    last_time = self.current_data.iloc[-1]['time'].timestamp() * 1000
                    self.chart.set_current_time(last_time)
    
    def update_time_label(self):
        """Обновляет метку времени под слайдером"""
        if self.current_data is not None and len(self.current_data) > self.current_index:
            dt = self.current_data.iloc[self.current_index]['time']
            self.time_label.setText(dt.strftime('%Y-%m-%d %H:%M'))
    
    def on_asset_changed(self, asset):
        """Переключение актива"""
        self.current_asset = asset
        # Здесь будет загрузка данных для нового актива
        # Пока генерируем новые фейковые данные
        self.data_raw = generate_mock_data(10000)
        self.aggregate_data()
        self.update_chart()
    
    def on_tf_changed(self, tf):
        """Переключение таймфрейма с сохранением позиции"""
        # Запоминаем текущее время (в миллисекундах)
        if self.current_data is not None and len(self.current_data) > self.current_index:
            self.current_position = self.current_data.iloc[self.current_index]['time'].timestamp() * 1000
        
        self.current_tf = tf
        self.aggregate_data()
        self.update_chart()
    
    def on_slider_changed(self, value):
        """Движение слайдера"""
        self.current_index = value
        self.update_time_label()
        
        # Перемещаем график
        if self.current_data is not None and len(self.current_data) > value:
            dt = self.current_data.iloc[value]['time'].timestamp() * 1000
            self.chart.set_current_time(dt)
    
    def on_play(self):
        """Запуск воспроизведения"""
        if self.is_playing:
            return
        self.is_playing = True
        self.btn_play.setText("⏸ Пауза")
        self.timer.start(100)  # 100 мс на свечу
    
    def on_stop(self):
        """Остановка"""
        self.is_playing = False
        self.btn_play.setText("▶ Play")
        self.timer.stop()
        self.status_label.setText("Статус: Остановлен")
    
    def play_step(self):
        """Один шаг воспроизведения (Bar-by-Bar)"""
        if self.current_data is None or len(self.current_data) == 0:
            self.on_stop()
            return
        
        # Переход к следующей свече
        self.current_index += 1
        if self.current_index >= len(self.current_data):
            self.on_stop()
            self.status_label.setText("Статус: История закончилась")
            return
        
        # Обновляем слайдер
        self.time_slider.setValue(self.current_index)
        
        # Здесь будет логика стратегии
        # Например, проверка пересечения скользящих средних
        self.status_label.setText(f"Статус: Обработка свечи {self.current_index}/{len(self.current_data)}")
        
        # Демо-торговля: просто обновляем баланс
        price = self.current_data.iloc[self.current_index]['close']
        self.balance_label.setText(f"Баланс: $10000 | PnL: ${price - 10000:.2f}")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    main()