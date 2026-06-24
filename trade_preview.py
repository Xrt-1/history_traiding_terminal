class TradePreview:
    """Управление примеркой позиции"""
    
    def __init__(self, chart_widget):
        self.chart = chart_widget
        self.is_active = False
        self.position_type = None  # 'long' или 'short'
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.take_profit = 0.0
        self.volume = 0.1  # Фиксированный объем
        self.lines = {}  # {'entry': id, 'sl': id, 'tp': id}
        
    def create_preview(self, price, position_type):
        """Создает примерку на текущей цене"""
        self.is_active = True
        self.position_type = position_type
        self.entry_price = price
        
        # Рассчитываем SL и TP (±2% для Long, ±2% для Short)
        if position_type == 'long':
            self.stop_loss = round(price * 0.98, 2)
            self.take_profit = round(price * 1.04, 2)
        else:  # short
            self.stop_loss = round(price * 1.02, 2)
            self.take_profit = round(price * 0.96, 2)
        
        # Рисуем линии
        self._draw_lines()
        return self.get_info()
    
    def _draw_lines(self):
        """Рисует линии на графике через chart_widget"""
        # Временно используем маркеры для отображения (пока нет API линий)
        # Позже заменим на реальные линии
        markers = []
        
        # Точка входа
        markers.append({
            'time': self._get_current_time(),
            'position': 'aboveBar',
            'color': '#4CAF50',
            'shape': 'arrowUp',
            'text': f'Entry: ${self.entry_price:.2f}'
        })
        
        # Стоп-лосс (красный)
        markers.append({
            'time': self._get_current_time(),
            'position': 'belowBar',
            'color': '#f44336',
            'shape': 'arrowDown',
            'text': f'SL: ${self.stop_loss:.2f}'
        })
        
        # Тейк-профит (зеленый)
        markers.append({
            'time': self._get_current_time(),
            'position': 'aboveBar',
            'color': '#4CAF50',
            'shape': 'arrowUp',
            'text': f'TP: ${self.take_profit:.2f}'
        })
        
        self.chart.set_markers(markers)
        self.lines = {'markers': markers}
    
    def _get_current_time(self):
        """Возвращает текущее время в миллисекундах"""
        # TODO: получить текущее время из графика
        import time
        return int(time.time() * 1000)
    
    def get_info(self):
        """Возвращает информацию о примерке"""
        if not self.is_active:
            return None
        
        # Расчет потенциальной прибыли/убытка
        if self.position_type == 'long':
            risk = (self.entry_price - self.stop_loss) * self.volume
            reward = (self.take_profit - self.entry_price) * self.volume
            pnl_at_sl = -risk
            pnl_at_tp = reward
        else:  # short
            risk = (self.stop_loss - self.entry_price) * self.volume
            reward = (self.entry_price - self.take_profit) * self.volume
            pnl_at_sl = -risk
            pnl_at_tp = reward
        
        risk_percent = (risk / self.entry_price) * 100 if self.entry_price > 0 else 0
        reward_percent = (reward / self.entry_price) * 100 if self.entry_price > 0 else 0
        rr_ratio = reward / risk if risk > 0 else 0
        
        return {
            'type': self.position_type.upper(),
            'entry': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'volume': self.volume,
            'risk_usd': risk,
            'reward_usd': reward,
            'risk_percent': risk_percent,
            'reward_percent': reward_percent,
            'rr_ratio': rr_ratio,
            'pnl_at_sl': pnl_at_sl,
            'pnl_at_tp': pnl_at_tp,
        }
    
    def update_sl(self, new_price):
        """Обновляет стоп-лосс (вызывается при движении линии)"""
        self.stop_loss = round(new_price, 2)
        self._update_lines()
    
    def update_tp(self, new_price):
        """Обновляет тейк-профит (вызывается при движении линии)"""
        self.take_profit = round(new_price, 2)
        self._update_lines()
    
    def _update_lines(self):
        """Обновляет линии на графике"""
        # TODO: обновлять линии без перерисовки всех маркеров
        self._draw_lines()
    
    def execute(self, balance_manager):
        """Подтверждает сделку"""
        if not self.is_active:
            return None
        
        # Проверяем достаточно ли средств
        required_margin = self.entry_price * self.volume * 0.01  # 1% маржа
        if balance_manager.balance < required_margin:
            return {'success': False, 'error': 'Недостаточно средств'}
        
        # Открываем позицию
        position = balance_manager.open_position(
            position_type=self.position_type,
            entry_price=self.entry_price,
            stop_loss=self.stop_loss,
            take_profit=self.take_profit,
            volume=self.volume
        )
        
        # Очищаем примерку
        self.cancel()
        
        return {'success': True, 'position': position}
    
    def cancel(self):
        """Отменяет примерку"""
        self.is_active = False
        self.position_type = None
        self.chart.set_markers([])
        self.lines = {}