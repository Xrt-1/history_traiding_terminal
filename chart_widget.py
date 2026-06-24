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
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        self.create_default_html(html_path)
        
        self.browser.setUrl(QUrl.fromLocalFile(html_path))
        self.browser.page().loadFinished.connect(self._on_loaded)
        
        self._loaded = False
        self._pending_data = None
        self._pending_append = None
        
    def create_default_html(self, path):
        html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Chart</title>
    <style>
        body { margin: 0; padding: 0; background: #1e222d; overflow: hidden; }
        #chart-container { width: 100vw; height: 100vh; }
    </style>
</head>
<body>
    <div id="chart-container"></div>
    <script src="https://unpkg.com/lightweight-charts@4.0.0/dist/lightweight-charts.standalone.production.js"></script>
    <script>
        const chart = LightweightCharts.createChart(document.getElementById('chart-container'), {
            width: document.getElementById('chart-container').clientWidth,
            height: document.getElementById('chart-container').clientHeight,
            layout: { 
                background: { color: '#1e222d' }, 
                textColor: '#d1d4dc' 
            },
            grid: { 
                vertLines: { color: '#2a2e39' }, 
                horzLines: { color: '#2a2e39' } 
            },
            timeScale: { 
                borderColor: '#2a2e39', 
                timeVisible: true, 
                secondsVisible: false,
                fixLeftEdge: true,    // Запрещаем скроллить левее данных
                fixRightEdge: false,  // РАЗРЕШАЕМ пустоту справа (будущее)
            },
            rightPriceScale: {
                borderColor: '#2a2e39',
            },
            handleScroll: true,
            handleScale: true,
        });
        
        const series = chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderDownColor: '#ef5350',
            borderUpColor: '#26a69a',
            wickDownColor: '#ef5350',
            wickUpColor: '#26a69a',
        });
        
        let fullData = [];
        let isDataLoaded = false;
        let lastShowCount = 300;
        let totalDataLength = 0;
        
        function updateChart(data) {
            if (!data || data.length === 0) {
                console.log('⚠️ No data to display');
                return;
            }
            
            fullData = data.map(item => ({
                time: Math.floor(item.time / 1000),
                open: item.open,
                high: item.high,
                low: item.low,
                close: item.close,
            }));
            
            totalDataLength = fullData.length;
            isDataLoaded = true;
            console.log('📊 Data loaded:', fullData.length, 'candles');
            
            series.setData(fullData);
            showLastBars(lastShowCount);
        }
        
        function appendData(newData) {
            if (!newData || newData.length === 0) return;
            
            const newCandles = newData.map(item => ({
                time: Math.floor(item.time / 1000),
                open: item.open,
                high: item.high,
                low: item.low,
                close: item.close,
            }));
            
            const allData = [...newCandles, ...fullData];
            
            const uniqueData = [];
            const timeSet = new Set();
            for (let i = allData.length - 1; i >= 0; i--) {
                if (!timeSet.has(allData[i].time)) {
                    timeSet.add(allData[i].time);
                    uniqueData.unshift(allData[i]);
                }
            }
            
            fullData = uniqueData;
            totalDataLength = fullData.length;
            
            console.log('📊 Appended data, total:', fullData.length, 'candles');
            
            const visibleRange = chart.timeScale().getVisibleLogicalRange();
            
            series.setData(fullData);
            
            if (visibleRange) {
                const from = visibleRange.from + (newCandles.length);
                const to = visibleRange.to + (newCandles.length);
                chart.timeScale().setVisibleLogicalRange({ 
                    from: Math.max(0, from), 
                    to: Math.min(totalDataLength, to) 
                });
            }
        }
        
        function showLastBars(count) {
            if (!isDataLoaded || fullData.length === 0) return;
            
            lastShowCount = count;
            const total = fullData.length;
            const barsToShow = Math.min(count, total);
            
            if (total > 0) {
                chart.timeScale().setVisibleLogicalRange({
                    from: Math.max(0, total - barsToShow),
                    to: total
                });
                console.log('📊 Showing last', barsToShow, 'bars (total:', total, ')');
            }
        }
        
        function setCurrentTime(timestamp) {
            if (!isDataLoaded || fullData.length === 0) return;
            
            const timeInSeconds = Math.floor(timestamp / 1000);
            
            let index = -1;
            for (let i = 0; i < fullData.length; i++) {
                if (fullData[i].time >= timeInSeconds) {
                    index = i;
                    break;
                }
            }
            
            if (index === -1) index = fullData.length - 1;
            
            const total = fullData.length;
            const halfBars = Math.floor(lastShowCount / 2);
            
            let from = Math.max(0, index - halfBars);
            let to = Math.min(total, index + halfBars);
            
            chart.timeScale().setVisibleLogicalRange({ from: from, to: to });
            console.log('📍 Set time to index:', index);
        }
        
        function fitContent() {
            if (!isDataLoaded || fullData.length === 0) return;
            chart.timeScale().fitContent();
        }
        
        function setTimeframe(tf) { 
            console.log('TF changed:', tf);
            setTimeout(function() {
                showLastBars(lastShowCount);
            }, 100);
        }
        
        function getVisibleRange() {
            return chart.timeScale().getVisibleLogicalRange();
        }
        
        function setMarkers(markers) {
            if (markers && markers.length > 0) {
                series.setMarkers(markers);
            } else {
                series.setMarkers([]);
            }
        }
        
        // ПОЛНОСТЬЮ ОТКЛЮЧАЕМ АВТОПОДГРУЗКУ ПРИ ПЕРЕТАСКИВАНИИ МЫШЬЮ
        function checkAndLoadMore() {
            return false;
        }
        
        // Отключаем подписку на изменения видимой области,
        // чтобы никакие события не вызывали checkAndLoadMore
        // chart.timeScale().subscribeVisibleLogicalRangeChange(...) - удаляем
        
        window.updateChart = updateChart;
        window.appendData = appendData;
        window.fitContent = fitContent;
        window.setCurrentTime = setCurrentTime;
        window.setTimeframe = setTimeframe;
        window.getVisibleRange = getVisibleRange;
        window.showLastBars = showLastBars;
        window.setMarkers = setMarkers;
        window.checkAndLoadMore = checkAndLoadMore;
        window.chart = chart;
        window.series = series;
        
        window.pyQtBridge = {
            loadMoreData: null
        };
        
        window.addEventListener('resize', function() {
            chart.resize(
                document.getElementById('chart-container').clientWidth,
                document.getElementById('chart-container').clientHeight
            );
        });
        
        console.log('✅ Chart initialized');
    </script>
</body>
</html>"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ HTML шаблон создан: {path}")
    
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
            data, callback = self._pending_data
            self._pending_data = None
            self._set_data_impl(data, callback)
        
        if self._pending_append is not None:
            data, callback = self._pending_append
            self._pending_append = None
            self._append_data_impl(data, callback)
    
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
        
        json_data = json.dumps(data)
        js_code = f"updateChart({json_data});"
        self.browser.page().runJavaScript(js_code)
        print(f"📊 Отправлено {len(data)} свечей на график")
        
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
    
    def set_data(self, df, callback=None):
        if not self._loaded:
            print("⏳ График загружается...")
            self._pending_data = (df, callback)
            return
        self._set_data_impl(df, callback)
    
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