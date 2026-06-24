# main.py - Минималистичный интерфейс в стиле Telegram/macOS
import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QComboBox, QSlider, QLabel, QMessageBox,
                             QFrame, QSplitter, QStackedWidget, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QFont, QColor, QPalette, QLinearGradient, QBrush, QPainter, QPen, QIcon, QPixmap, QPainterPath
import pandas as pd
from style_manager import StyleManager  # ← новый импорт

from data_fetcher import BinanceFetcher
from data_aggregator import DataAggregator
from chart_widget import ChartWidget


class ModernButton(QPushButton):
    """Кнопка с плавной анимацией"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._opacity = 1.0
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(150)
        
    def enterEvent(self, event):
        self.animation.stop()
        self.animation.setEndValue(0.7)
        self.animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.animation.stop()
        self.animation.setEndValue(1.0)
        self.animation.start()
        super().leaveEvent(event)
        
    def get_opacity(self):
        return self._opacity
    
    def set_opacity(self, value):
        self._opacity = value
        self.update()
        
    opacity = pyqtProperty(float, get_opacity, set_opacity)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()  # ← Убрал дублирование super().__init__()
        self.setWindowTitle("TradeView")
        self.setGeometry(100, 100, 1400, 880)
        self.setMinimumSize(1100, 700)
        
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
        
        # Применяем тень к окну
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setup_window_controls()
        
    def setup_window_controls(self):
        """Создает кастомные кнопки управления окном"""
        # Это будет в верхней панели
        pass
        
    def setup_ui(self):
        # Центральный виджет с прозрачным фоном
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        
        # Основной вертикальный макет
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # ========== ВЕРХНЯЯ ПАНЕЛЬ ==========
        top_panel = QWidget()
        top_panel.setObjectName("topPanel")
        top_panel.setFixedHeight(56)
        top_panel_layout = QHBoxLayout(top_panel)
        top_panel_layout.setContentsMargins(20, 8, 20, 8)
        top_panel_layout.setSpacing(12)
        
        # Логотип / Заголовок
        title_label = QLabel("📊 TradeView")
        title_label.setObjectName("titleLabel")
        top_panel_layout.addWidget(title_label)
        
        # Разделитель
        sep = QLabel("|")
        sep.setStyleSheet("color: rgba(0,0,0,0.15); font-size: 20px;")
        top_panel_layout.addWidget(sep)
        
        # Выбор актива
        asset_label = QLabel("Актив")
        asset_label.setStyleSheet("color: #8e8e93; font-size: 12px; font-weight: 500;")
        top_panel_layout.addWidget(asset_label)
        
        self.asset_combo = QComboBox()
        self.asset_combo.addItems(['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'])
        self.asset_combo.setFixedWidth(110)
        self.asset_combo.currentTextChanged.connect(self.on_asset_changed)
        top_panel_layout.addWidget(self.asset_combo)
        
        # Таймфрейм
        tf_label = QLabel("ТФ")
        tf_label.setStyleSheet("color: #8e8e93; font-size: 12px; font-weight: 500;")
        top_panel_layout.addWidget(tf_label)
        
        self.tf_combo = QComboBox()
        self.tf_combo.addItems(['1m', '5m', '15m', '1H', '4H', '1D', '1W'])
        self.tf_combo.setCurrentText('1H')
        self.tf_combo.setFixedWidth(70)
        self.tf_combo.currentTextChanged.connect(self.on_tf_changed)
        top_panel_layout.addWidget(self.tf_combo)
        
        top_panel_layout.addSpacing(8)
        
        # Кнопка обновить
        self.btn_refresh = ModernButton("⟳")
        self.btn_refresh.setFixedSize(34, 34)
        self.btn_refresh.setStyleSheet("font-size: 18px;")
        self.btn_refresh.setToolTip("Обновить данные")
        self.btn_refresh.clicked.connect(self.on_refresh)
        top_panel_layout.addWidget(self.btn_refresh)
        
        top_panel_layout.addStretch()
        
        # Информация о данных
        self.data_info_label = QLabel("")
        self.data_info_label.setObjectName("infoLabel")
        top_panel_layout.addWidget(self.data_info_label)
        
        # Разделитель
        sep2 = QLabel("|")
        sep2.setStyleSheet("color: rgba(0,0,0,0.15); font-size: 20px;")
        top_panel_layout.addWidget(sep2)
        
        # Баланс
        self.balance_label = QLabel("$10,000.00")
        self.balance_label.setObjectName("balanceLabel")
        top_panel_layout.addWidget(self.balance_label)
        
        # PnL
        self.pnl_label = QLabel("$0.00")
        self.pnl_label.setObjectName("pnlLabel")
        top_panel_layout.addWidget(self.pnl_label)
        
        main_layout.addWidget(top_panel)
        
        # ========== ГРАФИК ==========
        # Контейнер графика с фоном
        chart_container = QWidget()
        chart_container.setStyleSheet("""
            background: #ffffff;
            border-radius: 0px;
        """)
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chart = ChartWidget()
        self.chart.load_more_data.connect(self.on_load_more_data)
        chart_layout.addWidget(self.chart)
        
        main_layout.addWidget(chart_container, stretch=1)
        
        # ========== НИЖНЯЯ ПАНЕЛЬ ==========
        bottom_panel = QWidget()
        bottom_panel.setObjectName("bottomPanel")
        bottom_panel.setStyleSheet("""
            #bottomPanel {
                background: rgba(255, 255, 255, 0.92);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border-top: 1px solid rgba(0, 0, 0, 0.06);
                padding: 8px 16px;
            }
        """)
        bottom_panel.setFixedHeight(100)
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(16, 6, 16, 6)
        bottom_layout.setSpacing(6)
        
        # --- Слайдер ---
        slider_row = QHBoxLayout()
        slider_row.setSpacing(12)
        
        # Иконка времени
        time_icon = QLabel("⏱")
        time_icon.setStyleSheet("font-size: 16px;")
        slider_row.addWidget(time_icon)
        
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(1000)
        self.time_slider.valueChanged.connect(self.on_slider_changed)
        slider_row.addWidget(self.time_slider)
        
        self.time_label = QLabel("--:--")
        self.time_label.setObjectName("timeLabel")
        slider_row.addWidget(self.time_label)
        
        self.position_label = QLabel("0 / 0")
        self.position_label.setObjectName("positionLabel")
        slider_row.addWidget(self.position_label)
        
        bottom_layout.addLayout(slider_row)
        
        # --- Кнопки управления ---
        controls_row = QHBoxLayout()
        controls_row.setSpacing(6)
        
        # Группа навигации
        nav_group = QWidget()
        nav_group.setObjectName("navGroup")  # ← добавил objectName
        nav_group.setStyleSheet("""
            QWidget#navGroup {
                background: rgba(0, 0, 0, 0.03);
                border-radius: 8px;
                padding: 2px;
            }
        """)
        nav_layout = QHBoxLayout(nav_group)
        nav_layout.setSpacing(2)
        nav_layout.setContentsMargins(4, 2, 4, 2)
        
        # Кнопки навигации
        nav_buttons = [
            ("◀◀", self.go_to_begin, "В начало"),      # или «
            ("◀", self.on_step_back, "Шаг назад"),      # или ‹
            ("▶", self.on_step_forward, "Шаг вперед"),  # или ›
            ("▶▶", self.go_to_end, "В конец")           # или »
        ]
        for icon, func, tip in nav_buttons:
            btn = ModernButton(icon)
            btn.setFixedSize(32, 30)
            btn.setToolTip(tip)
            btn.setStyleSheet("font-size: 14px;")
            btn.clicked.connect(func)
            nav_layout.addWidget(btn)
        
        controls_row.addWidget(nav_group)
        
        controls_row.addSpacing(8)
        
        # Кнопка Play
        self.btn_play = QPushButton("▶ Воспроизвести")
        self.btn_play.setObjectName("playBtn")
        self.btn_play.setFixedSize(130, 34)
        self.btn_play.clicked.connect(self.on_play)
        controls_row.addWidget(self.btn_play)
        
        controls_row.addSpacing(8)
        
        # Скорость
        speed_label = QLabel("Скорость")
        speed_label.setStyleSheet("color: #8e8e93; font-size: 12px; font-weight: 500;")
        controls_row.addWidget(speed_label)
        
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(['0.1x', '0.25x', '0.5x', '1x', '2x', '5x', '10x'])
        self.speed_combo.setCurrentText('1x')
        self.speed_combo.setFixedWidth(65)
        self.speed_combo.currentTextChanged.connect(self.on_speed_changed)
        controls_row.addWidget(self.speed_combo)
        
        controls_row.addStretch()
        
        # Статус
        self.status_label = QLabel("✅ Готов")
        self.status_label.setObjectName("statusLabel")
        controls_row.addWidget(self.status_label)
        
        bottom_layout.addLayout(controls_row)
        main_layout.addWidget(bottom_panel)
        
        # --- Таймер ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.play_step)
        
        # Обновляем информацию
        self.update_balance_display()
        
    def get_speed_ms(self) -> int:
        speed_text = self.speed_combo.currentText()
        speed = float(speed_text.replace('x', ''))
        base_ms = 100
        return int(base_ms / speed)
    
    def load_data(self, symbol: str, force_refresh: bool = False):
        self.status_label.setText("⏳ Загрузка...")
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
            
            total_bars = len(self.full_data)
            if total_bars > 300:
                self.current_index = total_bars - 300
            else:
                self.current_index = 0
            
            self.current_position_ms = None
            
            self.update_slider()
            self.update_chart(reset_view=True)
            self.update_info()
            
            self.status_label.setText(f"✅ {symbol} · {total_bars} свечей")
            
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
    
    def update_chart(self, reset_view: bool = False):
        if self.full_data is None or self.full_data.empty:
            return
        
        total_bars = len(self.full_data)
        
        if self.current_index >= total_bars:
            self.current_index = total_bars - 1
        if self.current_index < 0:
            self.current_index = 0
        
        history_buffer = 1000
        to_idx = self.current_index + 1
        from_idx = max(0, to_idx - history_buffer)
        
        trimmed = self.full_data.iloc[from_idx:to_idx].copy()
        
        if trimmed.empty:
            return
        
        self.chart.set_data(trimmed, reset_view=reset_view)
        
    def update_slider(self):
        if self.full_data is not None and not self.full_data.empty:
            max_val = len(self.full_data) - 1
            
            self.time_slider.blockSignals(True)
            self.time_slider.setMaximum(max(0, max_val))
            self.time_slider.setValue(min(self.current_index, max_val))
            self.time_slider.blockSignals(False)
            
            self.update_time_label()
            
    def update_time_label(self):
        if self.full_data is not None and not self.full_data.empty:
            max_idx = len(self.full_data) - 1
            idx = min(self.current_index, max_idx)
            
            dt = self.full_data.iloc[idx]['time']
            self.time_label.setText(dt.strftime('%d.%m.%Y %H:%M'))
            self.position_label.setText(f"{idx + 1} / {max_idx + 1}")
    
    def update_info(self):
        if self.full_data is not None and not self.full_data.empty:
            start = self.full_data.iloc[0]['time'].strftime('%d.%m.%Y')
            end = self.full_data.iloc[-1]['time'].strftime('%d.%m.%Y')
            self.data_info_label.setText(f"{len(self.full_data)} свечей · {start} → {end}")
    
    def update_balance_display(self):
        pnl = self.balance - 10000
        color = "#34c759" if pnl >= 0 else "#ff3b30"
        
        self.balance_label.setText(f"${self.balance:,.2f}")
        self.pnl_label.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 15px;")
        self.pnl_label.setText(f"{'+' if pnl >= 0 else ''}{pnl:,.2f}")
    
    def go_to_begin(self):
        if self.is_playing:
            self.on_stop()
        self.current_index = 0
        self.time_slider.setValue(0)
        self.update_chart(reset_view=True)
        self.update_time_label()
    
    def go_to_end(self):
        if self.is_playing:
            self.on_stop()
        if self.full_data is not None and not self.full_data.empty:
            self.current_index = len(self.full_data) - 1
            self.time_slider.setValue(self.current_index)
            self.update_chart(reset_view=True)
            self.update_time_label()
    
    def on_asset_changed(self, symbol):
        if symbol != self.current_symbol:
            self.current_symbol = symbol
            self.current_position_ms = None
            self.current_index = 0
            self.load_data(symbol)
    
    def on_tf_changed(self, tf):
        if tf == self.current_tf:
            return
        
        if self.full_data is not None and not self.full_data.empty:
            idx = min(self.current_index, len(self.full_data) - 1)
            current_time = self.full_data.iloc[idx]['time']
            self.current_position_ms = int(current_time.timestamp() * 1000)
        
        self.current_tf = tf
        
        if self.aggregator is not None:
            self.full_data = self.aggregator.aggregate(tf)
            
            if self.full_data.empty:
                QMessageBox.warning(self, "Предупреждение", f"Нет данных для {tf}")
                self.tf_combo.setCurrentText(self.current_tf)
                return
            
            total_bars = len(self.full_data)
            
            if self.current_position_ms is not None:
                new_idx = self.find_nearest_index(self.current_position_ms)
                
                target_time = pd.to_datetime(self.current_position_ms, unit='ms')
                new_time = self.full_data.iloc[new_idx]['time']
                time_diff = abs((new_time - target_time).total_seconds() / 3600)
                
                if time_diff > 48:
                    if total_bars > 300:
                        new_idx = total_bars - 300
                    else:
                        new_idx = 0
                elif new_idx >= total_bars:
                    new_idx = total_bars - 1
                elif new_idx < 0:
                    new_idx = 0
            else:
                if total_bars > 300:
                    new_idx = total_bars - 300
                else:
                    new_idx = 0
            
            self.current_index = new_idx
            
            self.update_info()
            self.update_slider()
            self.update_chart(reset_view=True)
            self.chart.set_timeframe(tf)
            
            self.status_label.setText(f"✅ {self.current_symbol} · {tf} · {total_bars} свечей")

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
        self.update_chart(reset_view=False)
        
    def on_play(self):
        if self.full_data is None or self.full_data.empty:
            return
        
        if self.current_index >= len(self.full_data) - 1:
            self.current_index = max(0, len(self.full_data) - 301)
            self.time_slider.setValue(self.current_index)
            self.update_chart(reset_view=True)
        
        if self.is_playing:
            self.is_playing = False
            self.timer.stop()
            self.btn_play.setText("▶ Воспроизвести")
            self.btn_play.setProperty("playing", False)
            self.btn_play.style().unpolish(self.btn_play)
            self.btn_play.style().polish(self.btn_play)
            self.status_label.setText("⏸ Пауза")
        else:
            self.is_playing = True
            self.btn_play.setText("⏸ Пауза")
            self.btn_play.setProperty("playing", True)
            self.btn_play.style().unpolish(self.btn_play)
            self.btn_play.style().polish(self.btn_play)
            self.timer.start(self.get_speed_ms())
            self.status_label.setText("▶ Воспроизведение...")
    
    def on_stop(self):
        self.is_playing = False
        self.timer.stop()
        self.btn_play.setText("▶ Воспроизвести")
        self.btn_play.setProperty("playing", False)
        self.btn_play.style().unpolish(self.btn_play)
        self.btn_play.style().polish(self.btn_play)
        self.status_label.setText("⏹ Остановлен")
    
    def on_step_back(self):
        if self.is_playing:
            return
        
        if self.full_data is not None and self.current_index > 0:
            self.current_index -= 1
            self.time_slider.setValue(self.current_index)
            self.update_chart(reset_view=False)
            self.update_time_label()
    
    def on_step_forward(self):
        if self.is_playing:
            return
        
        if self.full_data is not None and self.current_index < len(self.full_data) - 1:
            self.current_index += 1
            self.time_slider.setValue(self.current_index)
            self.update_chart(reset_view=False)
            self.update_time_label()
    
    def play_step(self):
        if self.full_data is None or self.full_data.empty:
            self.on_stop()
            return
        
        if self.current_index >= len(self.full_data) - 1:
            self.on_stop()
            self.status_label.setText("✅ История закончилась")
            self.btn_play.setText("▶ Воспроизвести")
            return
        
        self.current_index += 1
        self.time_slider.setValue(self.current_index)
    
    def on_load_more_data(self, timestamp_ms):
        if self.is_playing:
            return
        
        if self.aggregator is None:
            return
        
        print(f"🔄 Запрос на подгрузку данных до {timestamp_ms}")
        
        if self.full_data is not None and not self.full_data.empty:
            first_time = self.full_data.iloc[0]['time']
            first_timestamp = int(first_time.timestamp() * 1000)
            
            if timestamp_ms >= first_timestamp:
                print("ℹ️ Данные уже загружены")
                return
        
        try:
            symbol = self.current_symbol
            tf = self.current_tf
            
            if hasattr(self.aggregator, 'load_more'):
                new_df = self.aggregator.load_more(
                    symbol=symbol,
                    interval='1m',
                    before_time=timestamp_ms,
                    count=300
                )
                
                if new_df is not None and not new_df.empty:
                    new_aggregated = self.aggregator.aggregate(
                        tf,
                        data=new_df
                    )
                    
                    if not new_aggregated.empty:
                        self.full_data = pd.concat([new_aggregated, self.full_data])
                        self.full_data = self.full_data.drop_duplicates(subset=['time'])
                        self.full_data = self.full_data.sort_values('time').reset_index(drop=True)
                        
                        self.chart.append_data(new_aggregated)
                        self.update_info()
                        self.update_slider()
                        
                        print(f"✅ Загружено {len(new_aggregated)} дополнительных свечей")
                        self.status_label.setText(f"📥 Загружено {len(new_aggregated)} свечей")
            else:
                print("⚠️ Метод load_more не реализован в DataAggregator")
                    
        except Exception as e:
            print(f"❌ Ошибка при подгрузке данных: {e}")
            self.status_label.setText(f"❌ Ошибка подгрузки")
    
    def closeEvent(self, event):
        self.on_stop()
        event.accept()


def main():
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)  # ← убрал дублирование
    
    # Настройка шрифтов
    font = QFont("-apple-system", 13)
    app.setFont(font)
    
    # Инициализация менеджера стилей и загрузка темы
    style_manager = StyleManager(app)
    style_manager.load_style('macos')  # или 'dark', 'light'
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()