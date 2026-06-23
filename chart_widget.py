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
        
        # Путь к HTML-шаблону
        html_path = os.path.join(os.path.dirname(__file__), 'resources', 'chart_template.html')
        
        # Проверяем существование файла
        if not os.path.exists(html_path):
            print(f"⚠️ HTML шаблон не найден: {html_path}")
            # Создаем директорию если её нет
            os.makedirs(os.path.dirname(html_path), exist_ok=True)
            # Можно создать базовый HTML здесь или использовать встроенный
            self.create_default_html(html_path)
        
        self.browser.setUrl(QUrl.fromLocalFile(html_path))
        
        # Ждем загрузки страницы
        self.browser.page().loadFinished.connect(self._on_loaded)
        self._loaded = False
        
    def create_default_html(self, path):
        """Создает базовый HTML файл если он не существует"""
        html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Chart</title>
    <style>
        body { margin: 0; padding: 0; background: #1e222d; }
        #chart-container { width: 100%; height: 100vh; }
    </style>
</head>
<body>
    <div id="chart-container"></div>
    <script src="https://unpkg.com/lightweight-charts@4.0.0/dist/lightweight-charts.standalone.production.js"></script>
    <script>
        const chart = LightweightCharts.createChart(document.getElementById('chart-container'), {
            width: document.getElementById('chart-container').clientWidth,
            height: document.getElementById('chart-container').clientHeight,
            layout: { background: { color: '#1e222d' }, textColor: '#d1d4dc' },
            grid: { vertLines: { color: '#2a2e39' }, horzLines: { color: '#2a2e39' } },
            timeScale: { borderColor: '#2a2e39', timeVisible: true, secondsVisible: false },
        });
        const series = chart.addCandlestickSeries({
            upColor: '#26a69a', downColor: '#ef5350',
            borderDownColor: '#ef5350', borderUpColor: '#26a69a',
            wickDownColor: '#ef5350', wickUpColor: '#26a69a',
        });
        
        function updateChart(data) {
            if (!data || data.length === 0) return;
            const chartData = data.map(item => ({
                time: Math.floor(item.time / 1000),
                open: item.open, high: item.high, low: item.low, close: item.close,
            }));
            series.setData(chartData);
            chart.timeScale().fitContent();
        }
        
        function setCurrentTime(timestamp) {
            const timeInSeconds = Math.floor(timestamp / 1000);
            chart.timeScale().setVisibleLogicalRange({
                from: timeInSeconds - 86400 * 30,
                to: timeInSeconds + 86400,
            });
        }
        
        function setTimeframe(tf) { console.log('TF:', tf); }
        
        window.updateChart = updateChart;
        window.setCurrentTime = setCurrentTime;
        window.setTimeframe = setTimeframe;
        window.chart = chart;
        window.series = series;
    </script>
</body>
</html>"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ Создан HTML шаблон: {path}")
        
    def _on_loaded(self):
        self._loaded = True
        print("✅ График загружен")
        
    def set_data(self, df):
        """Передает данные в JavaScript"""
        if not self._loaded:
            print("⚠️ График еще не загружен")
            return
        
        if df is None or df.empty:
            print("⚠️ Нет данных для отображения")
            return
            
        # Преобразуем DataFrame в список словарей для JSON
        data = df[['time', 'open', 'high', 'low', 'close']].to_dict('records')
        
        # Конвертируем время в миллисекунды (JavaScript Date)
        for item in data:
            if isinstance(item['time'], pd.Timestamp):
                item['time'] = int(item['time'].timestamp() * 1000)
            else:
                # Если это уже timestamp
                item['time'] = int(item['time'])
        
        json_data = json.dumps(data)
        
        # Вызываем JS-функцию updateChart
        js_code = f"updateChart({json_data});"
        self.browser.page().runJavaScript(js_code)
        print(f"📊 Отправлено {len(data)} свечей на график")
    
    def set_timeframe(self, tf_label):
        """Меняет ТФ на графике"""
        js_code = f"setTimeframe('{tf_label}');"
        self.browser.page().runJavaScript(js_code)
    
    def set_current_time(self, timestamp):
        """Перемещает график на указанную дату (в миллисекундах)"""
        if not self._loaded:
            return
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
        
    def set_markers(self, markers):
        """
        markers: список словарей [
            {'time': timestamp_ms, 'position': 'aboveBar'/'belowBar', 
            'color': 'green'/'red', 'shape': 'arrowUp'/'arrowDown', 'text': 'BUY'}
        ]
        """
        if not markers:
            js_code = "series.setMarkers([]);"
        else:
            js_code = f"series.setMarkers({json.dumps(markers)});"
        
        self.browser.page().runJavaScript(js_code)