import json
import os
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, pyqtSignal, QObject
from PyQt5.QtWidgets import QVBoxLayout, QWidget
import pandas as pd

class ChartWidget(QWidget):
    # Сигнал, когда пользователь кликнул на график (вернет время)
    time_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.browser = QWebEngineView()
        layout.addWidget(self.browser)
        
        # Путь к HTML-шаблону (создадим ниже)
        html_path = os.path.join(os.path.dirname(__file__), 'resources', 'chart_template.html')
        self.browser.setUrl(QUrl.fromLocalFile(html_path))
        
        # Ждем загрузки страницы
        self.browser.page().loadFinished.connect(self._on_loaded)
        self._loaded = False
        
    def _on_loaded(self):
        self._loaded = True
        
    def set_data(self, df):
        """Передает данные в JavaScript"""
        if not self._loaded:
            return
            
        # Преобразуем DataFrame в список словарей для JSON
        data = df[['time', 'open', 'high', 'low', 'close']].to_dict('records')
        
        # Конвертируем время в миллисекунды (JavaScript Date)
        for item in data:
            item['time'] = int(item['time'].timestamp() * 1000)
        
        json_data = json.dumps(data)
        
        # Вызываем JS-функцию updateChart
        js_code = f"updateChart({json_data});"
        self.browser.page().runJavaScript(js_code)
    
    def set_timeframe(self, tf_label):
        """Меняет ТФ на графике"""
        js_code = f"setTimeframe('{tf_label}');"
        self.browser.page().runJavaScript(js_code)
    
    def set_current_time(self, timestamp):
        """Перемещает график на указанную дату (в миллисекундах)"""
        js_code = f"setCurrentTime({timestamp});"
        self.browser.page().runJavaScript(js_code)
    
    def get_current_time(self, callback):
        """Запрашивает текущую позицию графика (асинхронно)"""
        js_code = """
        (function() {
            return chart.timeScale().getVisibleLogicalRange();
        })();
        """
        self.browser.page().runJavaScript(js_code, callback)