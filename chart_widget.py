# name: chart_widget.py
import json
import os
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, pyqtSignal, QTimer
from PyQt5.QtWidgets import QVBoxLayout, QWidget
import pandas as pd

class ChartWidget(QWidget):
    time_selected = pyqtSignal(str)
    load_more_data = pyqtSignal(int)  # Сигнал для запроса загрузки данных
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.browser = QWebEngineView()
        layout.addWidget(self.browser)
        
        html_path = os.path.join(os.path.dirname(__file__), 'resources', 'chart_template.html')
        # Проверяем, существует ли файл
        if not os.path.exists(html_path):
            # Если нет - создаем базовый или копируем из другого места
            print(f"⚠️ Файл {html_path} не найден!")
            # Создаем минимальный HTML
            os.makedirs(os.path.dirname(html_path), exist_ok=True)
            self.create_default_html(html_path)
        # Используем существующий файл
        self.browser.setUrl(QUrl.fromLocalFile(html_path))

        self.browser.page().loadFinished.connect(self._on_loaded)
        
        self._loaded = False
        self._pending_data = None
        self._pending_append = None
        
   
    def _on_loaded(self):
        self._loaded = True
        print("✅ График загружен")
        
        js_code = """
        (function() {
            window.pyQtBridge.loadMoreData = function(timestamp) {
                console.log('loadMoreData: ' + timestamp);
                return true;
            };
        })();
        """
        self.browser.page().runJavaScript(js_code)
        
        if self._pending_data is not None:
            data, reset_view, callback = self._pending_data
            self._pending_data = None
            self._set_data_impl(data, reset_view, callback)
        
        if self._pending_append is not None:
            data, callback = self._pending_append
            self._pending_append = None
            self._append_data_impl(data, callback)
    
    def _set_data_impl(self, df, reset_view=False, callback=None):
        if df is None or df.empty:
            print("⚠️ Нет данных для отображения")
            return
        
        data = df[['time', 'open', 'high', 'low', 'close']].to_dict('records')
        
        for item in data:
            if isinstance(item['time'], pd.Timestamp):
                item['time'] = int(item['time'].timestamp() * 1000)
            else:
                item['time'] = int(item['time'])
        
        json_data = json.dumps(data)
        js_code = f"updateChart({json_data}, {'true' if reset_view else 'false'});"
        self.browser.page().runJavaScript(js_code)
        print(f"📊 Отправлено {len(data)} свечей на график (reset_view={reset_view})")
        
        if callback:
            callback()
    
    def append_data(self, df, callback=None):
        """Добавление новых данных к существующим (для подгрузки истории)"""
        if not self._loaded:
            print("⏳ График загружается...")
            self._pending_append = (df, callback)
            return
        self._append_data_impl(df, callback)
    
    def _append_data_impl(self, df, callback=None):
        if df is None or df.empty:
            print("⚠️ Нет данных для добавления")
            return
        
        data = df[['time', 'open', 'high', 'low', 'close']].to_dict('records')
        
        for item in data:
            if isinstance(item['time'], pd.Timestamp):
                item['time'] = int(item['time'].timestamp() * 1000)
            else:
                item['time'] = int(item['time'])
        
        json_data = json.dumps(data)
        js_code = f"appendData({json_data});"
        self.browser.page().runJavaScript(js_code)
        print(f"📊 Добавлено {len(data)} свечей к графику")
        
        if callback:
            callback()
    
    def set_data(self, df, reset_view=False, callback=None):
        if not self._loaded:
            print("⏳ График загружается...")
            self._pending_data = (df, reset_view, callback)
            return
        self._set_data_impl(df, reset_view, callback)
    
    def fit_content(self):
        if not self._loaded:
            return
        self.browser.page().runJavaScript("if (window.fitContent) window.fitContent();")
    
    def show_last_bars(self, count=300):
        if not self._loaded:
            return
        js_code = f"if (window.showLastBars) {{ window.showLastBars({count}); }}"
        self.browser.page().runJavaScript(js_code)
    
    def set_timeframe(self, tf_label):
        if not self._loaded:
            return
        js_code = f"if (window.setTimeframe) {{ window.setTimeframe('{tf_label}'); }}"
        self.browser.page().runJavaScript(js_code)
    
    def set_current_time(self, timestamp):
        if not self._loaded:
            return
        js_code = f"if (window.setCurrentTime) {{ window.setCurrentTime({timestamp}); }}"
        self.browser.page().runJavaScript(js_code)
    
    def get_current_time(self, callback):
        js_code = """
        (function() {
            if (window.getVisibleRange) {
                return window.getVisibleRange();
            }
            return null;
        })();
        """
        self.browser.page().runJavaScript(js_code, callback)
    
    def set_markers(self, markers):
        if not self._loaded:
            return
        
        if markers:
            js_code = f"if (window.setMarkers) {{ window.setMarkers({json.dumps(markers)}); }}"
        else:
            js_code = "if (window.setMarkers) { window.setMarkers([]); }"
        self.browser.page().runJavaScript(js_code)

    