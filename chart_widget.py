import json
import os
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, pyqtSignal, QTimer
from PyQt5.QtWidgets import QVBoxLayout, QWidget
import pandas as pd

class ChartWidget(QWidget):
    time_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.browser = QWebEngineView()
        layout.addWidget(self.browser)
        
        html_path = os.path.join(os.path.dirname(__file__), 'resources', 'chart_template.html')
        
        if not os.path.exists(html_path):
            print(f"⚠️ HTML шаблон не найден: {html_path}")
            os.makedirs(os.path.dirname(html_path), exist_ok=True)
            self.create_default_html(html_path)
        
        self.browser.setUrl(QUrl.fromLocalFile(html_path))
        
        self.browser.page().loadFinished.connect(self._on_loaded)
        self._loaded = False
        self._pending_data = None
        self._data_count = 0
        self._bars_to_show = 500  # Количество отображаемых свечей
        
    def create_default_html(self, path):
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
            timeScale: { 
                borderColor: '#2a2e39', 
                timeVisible: true, 
                secondsVisible: false,
            },
        });
        const series = chart.addCandlestickSeries({
            upColor: '#26a69a', downColor: '#ef5350',
            borderDownColor: '#ef5350', borderUpColor: '#26a69a',
            wickDownColor: '#ef5350', wickUpColor: '#26a69a',
        });
        
        let chartData = [];
        let isDataLoaded = false;
        let fullData = [];  // Храним все данные
        let visibleCount = 500;  // По умолчанию показываем 500 свечей
        
        function updateChart(data) {
            if (!data || data.length === 0) return;
            
            // Сохраняем все данные
            fullData = data.map(item => ({
                time: Math.floor(item.time / 1000),
                open: item.open, high: item.high, low: item.low, close: item.close,
            }));
            
            // Показываем только последние N свечей
            updateVisibleData();
            isDataLoaded = true;
            console.log('Total data loaded:', fullData.length);
        }
        
        function updateVisibleData() {
            if (fullData.length === 0) return;
            
            // Берем последние visibleCount свечей
            const start = Math.max(0, fullData.length - visibleCount);
            chartData = fullData.slice(start);
            
            series.setData(chartData);
            console.log('Showing', chartData.length, 'bars (from', start, 'to', fullData.length, ')');
            
            // Подгоняем масштаб под видимые данные
            chart.timeScale().fitContent();
        }
        
        function setVisibleBars(count) {
            visibleCount = Math.max(10, count);
            if (isDataLoaded) {
                updateVisibleData();
            }
        }
        
        function showLastBars(count) {
            if (!isDataLoaded || fullData.length === 0) return;
            
            const total = fullData.length;
            const barsToShow = Math.min(count, total);
            const from = Math.max(0, total - barsToShow);
            const to = total;
            
            // Обновляем видимые данные
            chartData = fullData.slice(from);
            series.setData(chartData);
            
            chart.timeScale().fitContent();
            console.log('Showing last', barsToShow, 'bars');
        }
        
        function fitContent() {
            if (!isDataLoaded || chartData.length === 0) return;
            chart.timeScale().fitContent();
            console.log('fitContent done');
        }
        
        function setCurrentTime(timestamp) {
            if (!isDataLoaded || fullData.length === 0) return;
            
            const timeInSeconds = Math.floor(timestamp / 1000);
            
            let index = 0;
            for (let i = 0; i < fullData.length; i++) {
                if (fullData[i].time >= timeInSeconds) {
                    index = i;
                    break;
                }
            }
            
            const totalBars = fullData.length;
            const barsToShow = Math.min(visibleCount, totalBars);
            const halfBars = Math.floor(barsToShow / 2);
            
            let from = Math.max(0, index - halfBars);
            let to = Math.min(totalBars, index + halfBars);
            
            if (to - from < barsToShow) {
                if (from === 0) {
                    to = Math.min(totalBars, barsToShow);
                } else if (to === totalBars) {
                    from = Math.max(0, totalBars - barsToShow);
                }
            }
            
            if (from < to) {
                // Показываем срез данных
                chartData = fullData.slice(from, to);
                series.setData(chartData);
                chart.timeScale().fitContent();
                console.log('setCurrentTime:', from, to);
            }
        }
        
        function setTimeframe(tf) { 
            console.log('TF changed:', tf);
            // После смены ТФ показываем последние 500 свечей
            setTimeout(function() {
                showLastBars(500);
            }, 100);
        }
        
        function getVisibleRange() {
            return chart.timeScale().getVisibleLogicalRange();
        }
        
        window.updateChart = updateChart;
        window.fitContent = fitContent;
        window.setCurrentTime = setCurrentTime;
        window.setTimeframe = setTimeframe;
        window.getVisibleRange = getVisibleRange;
        window.showLastBars = showLastBars;
        window.setVisibleBars = setVisibleBars;
        window.chart = chart;
        window.series = series;
        
        console.log('Chart initialized');
    </script>
</body>
</html>"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ Создан HTML шаблон: {path}")
        
    def _on_loaded(self):
        self._loaded = True
        print("✅ График загружен")
        
        if self._pending_data is not None:
            data, callback = self._pending_data
            self._pending_data = None
            self._set_data_impl(data, callback)
        
    def _set_data_impl(self, df, callback=None):
        if df is None or df.empty:
            print("⚠️ Нет данных для отображения")
            return
            
        data = df[['time', 'open', 'high', 'low', 'close']].to_dict('records')
        
        for item in data:
            if isinstance(item['time'], pd.Timestamp):
                item['time'] = int(item['time'].timestamp() * 1000)
            else:
                item['time'] = int(item['time'])
        
        self._data_count = len(data)
        json_data = json.dumps(data)
        
        # Передаем данные на график
        js_code = f"updateChart({json_data});"
        self.browser.page().runJavaScript(js_code)
        print(f"📊 Отправлено {len(data)} свечей на график")
        
        # Даем время на отрисовку и показываем последние свечи
        QTimer.singleShot(300, lambda: self.show_last_bars(500))
        
        if callback:
            callback()  
    def set_data(self, df, callback=None):
        if not self._loaded:
            print("⏳ График загружается, данные будут отображены позже...")
            self._pending_data = (df, callback)
            return
        
        self._set_data_impl(df, callback)
    
    def fit_content(self):
        if not self._loaded:
            return
        js_code = "if (window.fitContent) { window.fitContent(); }"
        self.browser.page().runJavaScript(js_code)
    
    def show_last_bars(self, count=500):
        """Показывает последние N свечей"""
        if not self._loaded:
            return
        js_code = f"if (window.showLastBars) {{ window.showLastBars({count}); }}"
        self.browser.page().runJavaScript(js_code)
        print(f"📊 Показываем последние {count} свечей")
    
    def set_visible_bars(self, count=500):
        """Устанавливает количество отображаемых свечей"""
        if not self._loaded:
            return
        js_code = f"if (window.setVisibleBars) {{ window.setVisibleBars({count}); }}"
        self.browser.page().runJavaScript(js_code)
    
    def set_timeframe(self, tf_label):
        js_code = f"if (window.setTimeframe) {{ window.setTimeframe('{tf_label}'); }}"
        self.browser.page().runJavaScript(js_code)
        # После смены ТФ показываем последние 500 свечей
        QTimer.singleShot(200, lambda: self.show_last_bars(500))
    
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
        if not markers:
            js_code = "if (window.series) { window.series.setMarkers([]); }"
        else:
            js_code = f"if (window.series) {{ window.series.setMarkers({json.dumps(markers)}); }}"
        
        self.browser.page().runJavaScript(js_code)