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
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        self.create_default_html(html_path)
        
        self.browser.setUrl(QUrl.fromLocalFile(html_path))
        self.browser.page().loadFinished.connect(self._on_loaded)
        
        self._loaded = False
        self._pending_data = None
        self._bars_to_show = 500
        self._max_bars_to_send = 5000
        self._batch_size = 1000
        
        self.full_data = None
        self.current_tf = None
        self._request_count = 0
        self._last_from_index = None
        self._pending_requests = set()  # Множество для избежания дубликатов
        
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
        
        let fullData = [];
        let isDataLoaded = false;
        let visibleCount = 500;
        let totalBarsAvailable = 0;
        let absoluteStartIndex = 0;  // Глобальный индекс начала данных
        let isRequesting = false;
        let lastRequestedIndex = -1;
        let checkTimeout = null;
        
        function updateChart(data, totalBars) {
            if (!data || data.length === 0) return;
            
            fullData = data.map(item => ({
                time: Math.floor(item.time / 1000),
                open: item.open, high: item.high, low: item.low, close: item.close,
            }));
            
            totalBarsAvailable = totalBars || fullData.length;
            isDataLoaded = true;
            absoluteStartIndex = Math.max(0, totalBarsAvailable - fullData.length);
            
            console.log('📊 Total data loaded:', fullData.length);
            console.log('📊 Absolute start index:', absoluteStartIndex);
            
            series.setData(fullData);
            showLastBars(visibleCount);
        }
        
        function showLastBars(count) {
            if (!isDataLoaded || fullData.length === 0) return;
            
            const total = fullData.length;
            const barsToShow = Math.min(count, total);
            
            chart.timeScale().setVisibleLogicalRange({
                from: total - barsToShow,
                to: total
            });
        }
        
        function addMoreDataLeft(newData) {
            if (!newData || newData.length === 0) {
                console.log('⚠️ No new data to add');
                isRequesting = false;
                return;
            }
            
            const newBars = newData.map(item => ({
                time: Math.floor(item.time / 1000),
                open: item.open, high: item.high, low: item.low, close: item.close,
            }));
            
            // Сохраняем текущую область видимости
            const range = chart.timeScale().getVisibleLogicalRange();
            
            // Добавляем данные слева
            fullData = newBars.concat(fullData);
            absoluteStartIndex = Math.max(0, absoluteStartIndex - newBars.length);
            
            series.setData(fullData);
            
            // Восстанавливаем позицию с учетом добавленных свечей
            if (range !== null) {
                const shift = newBars.length;
                chart.timeScale().setVisibleLogicalRange({
                    from: Math.max(0, range.from + shift),
                    to: Math.min(fullData.length, range.to + shift)
                });
            }
            
            isRequesting = false;
            console.log('✅ Updated. New total:', fullData.length, 'Absolute start index:', absoluteStartIndex);
        }
        
        function requestMoreData(fromIndex) {
            // Защита от множественных запросов
            if (isRequesting) {
                console.log('⏳ Already requesting, skipping...');
                return;
            }
            
            if (fromIndex === lastRequestedIndex) {
                console.log('🔄 Same index requested, skipping...');
                return;
            }
            
            if (fromIndex <= 0) {
                console.log('📌 Reached beginning of data');
                return;
            }
            
            console.log('🔵 Requesting more data from index:', fromIndex);
            isRequesting = true;
            lastRequestedIndex = fromIndex;
            
            // Отправляем запрос в Python
            if (window.pyqtLoadMoreData) {
                window.pyqtLoadMoreData(fromIndex);
            }
        }
        
        function checkAndRequestMore() {
            if (!isDataLoaded || fullData.length === 0 || isRequesting) return;
            
            try {
                const range = chart.timeScale().getVisibleLogicalRange();
                if (!range) return;
                
                const from = Math.floor(range.from);
                const visibleBars = Math.floor(range.to - range.from);
                
                // Проверяем, есть ли куда подгружать
                if (absoluteStartIndex <= 0) {
                    console.log('📌 No more data to load (start reached)');
                    return;
                }
                
                // Если видим меньше 30 свечей - подгружаем
                if (visibleBars < 30) {
                    console.log('🔄 Few bars visible, requesting more...');
                    requestMoreData(absoluteStartIndex);
                    return;
                }
                
                // Если подошли к левому краю
                if (from < 5) {
                    console.log('🔄 Near left edge, requesting history...');
                    requestMoreData(absoluteStartIndex);
                }
            } catch(e) {
                console.log('❌ Error in checkAndRequestMore:', e);
            }
        }
        
        // Подписываемся на изменения видимого диапазона
        chart.timeScale().subscribeVisibleLogicalRangeChange(function(range) {
            if (!range || !isDataLoaded || fullData.length === 0) return;
            
            // Используем debounce для предотвращения спама
            clearTimeout(checkTimeout);
            checkTimeout = setTimeout(checkAndRequestMore, 200);
        });
        
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
            const barsToShow = Math.min(visibleCount, total);
            const halfBars = Math.floor(barsToShow / 2);
            
            let from = Math.max(0, index - halfBars);
            let to = Math.min(total, index + halfBars);
            
            chart.timeScale().setVisibleLogicalRange({ from: from, to: to });
        }
        
        function setTimeframe(tf) { 
            console.log('TF changed:', tf);
            setTimeout(function() {
                showLastBars(visibleCount);
            }, 100);
        }
        
        function fitContent() {
            if (!isDataLoaded || fullData.length === 0) return;
            chart.timeScale().fitContent();
        }
        
        function getVisibleRange() {
            return chart.timeScale().getVisibleLogicalRange();
        }
        
        // Экспортируем функции
        window.updateChart = updateChart;
        window.fitContent = fitContent;
        window.setCurrentTime = setCurrentTime;
        window.setTimeframe = setTimeframe;
        window.getVisibleRange = getVisibleRange;
        window.showLastBars = showLastBars;
        window.addMoreDataLeft = addMoreDataLeft;
        window.requestMoreData = requestMoreData;
        window.checkAndRequestMore = checkAndRequestMore;
        window.chart = chart;
        window.series = series;
        window._pendingRequests = [];
        
        console.log('✅ Chart initialized');
    </script>
</body>
</html>"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ Создан HTML шаблон: {path}")
    
    def _on_loaded(self):
        self._loaded = True
        print("✅ График загружен")
        
        # Регистрируем функцию для приема запросов
        self.browser.page().runJavaScript("""
        window.pyqtLoadMoreData = function(fromIndex) {
            if (window._pendingRequests === undefined) {
                window._pendingRequests = [];
            }
            // Добавляем запрос, если его нет в очереди
            if (!window._pendingRequests.includes(fromIndex)) {
                window._pendingRequests.push(fromIndex);
            }
            console.log('📥 Request added to queue:', fromIndex);
        };
        """)
        
        if self._pending_data is not None:
            data, callback = self._pending_data
            self._pending_data = None
            self._set_data_impl(data, callback)
        
        # Запускаем таймер для обработки запросов
        self._check_timer = QTimer()
        self._check_timer.timeout.connect(self._check_pending_requests)
        self._check_timer.start(300)  # Проверяем раз в 300 мс
    
    def _check_pending_requests(self):
        """Проверяет наличие запросов от JavaScript"""
        self.browser.page().runJavaScript("""
        (function() {
            if (window._pendingRequests && window._pendingRequests.length > 0) {
                var requests = window._pendingRequests.slice();
                window._pendingRequests = [];
                return requests;
            }
            return null;
        })();
        """, self._handle_pending_requests)
    
    def _handle_pending_requests(self, result):
        """Обрабатывает полученные запросы"""
        if not result:
            return
        
        # Удаляем дубликаты и сортируем (от большего к меньшему)
        unique_requests = sorted(set(result), reverse=True)
        
        for from_index in unique_requests:
            # Проверяем, не обрабатывали ли уже этот индекс
            if from_index in self._pending_requests:
                continue
            
            self._pending_requests.add(from_index)
            
            # Проверяем, что индекс в пределах данных
            if self.full_data is not None and from_index <= len(self.full_data):
                self._load_more_data(from_index)
            
            # Удаляем из множества после обработки
            self._pending_requests.discard(from_index)
    
    def _set_data_impl(self, df, callback=None):
        if df is None or df.empty:
            print("⚠️ Нет данных для отображения")
            return
        
        self.full_data = df.copy()
        total_bars = len(df)
        
        # Загружаем только последние свечи для быстрой инициализации
        initial_data = df.tail(self._max_bars_to_send)
        
        data = initial_data[['time', 'open', 'high', 'low', 'close']].to_dict('records')
        
        for item in data:
            if isinstance(item['time'], pd.Timestamp):
                item['time'] = int(item['time'].timestamp() * 1000)
            else:
                item['time'] = int(item['time'])
        
        json_data = json.dumps(data)
        
        js_code = f"updateChart({json_data}, {total_bars});"
        self.browser.page().runJavaScript(js_code)
        print(f"📊 Отправлено {len(data)} свечей (из {total_bars}) на график")
        
        if callback:
            callback()
    
    def _load_more_data(self, from_index):
        """Загружает дополнительные данные слева"""
        self._request_count += 1
        print(f"🔵 Запрос на подгрузку данных #{self._request_count} с индекса {from_index}")
        
        if self.full_data is None or self.full_data.empty:
            print("⚠️ Нет данных для загрузки")
            return
        
        if from_index <= 0:
            print("📌 Достигли начала данных")
            return
        
        # Вычисляем диапазон для загрузки
        batch_size = self._batch_size
        start_idx = max(0, from_index - batch_size)
        end_idx = from_index
        
        # Проверяем, есть ли новые данные
        if start_idx == end_idx:
            print("📌 Больше нет данных для подгрузки")
            return
        
        new_data = self.full_data.iloc[start_idx:end_idx].copy()
        
        if new_data.empty:
            print("📌 Больше нет данных для подгрузки")
            return
        
        print(f"📥 Загружено дополнительно {len(new_data)} свечей (с {start_idx} по {end_idx})")
        
        data = new_data[['time', 'open', 'high', 'low', 'close']].to_dict('records')
        for item in data:
            if isinstance(item['time'], pd.Timestamp):
                item['time'] = int(item['time'].timestamp() * 1000)
            else:
                item['time'] = int(item['time'])
        
        json_data = json.dumps(data)
        
        # Отправляем данные в JavaScript
        js_code = f"if (window.addMoreDataLeft) {{ window.addMoreDataLeft({json_data}); }}"
        self.browser.page().runJavaScript(js_code)
    
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
        if not self._loaded:
            return
        js_code = f"if (window.showLastBars) {{ window.showLastBars({count}); }}"
        self.browser.page().runJavaScript(js_code)
        print(f"📊 Показываем последние {count} свечей")
    
    def set_timeframe(self, tf_label):
        js_code = f"if (window.setTimeframe) {{ window.setTimeframe('{tf_label}'); }}"
        self.browser.page().runJavaScript(js_code)
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