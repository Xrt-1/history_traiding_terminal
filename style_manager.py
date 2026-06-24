# style_manager.py
import os
from PyQt5.QtCore import QFile, QTextStream

class StyleManager:
    """Управление стилями приложения"""
    
    THEMES = {
        'light': 'styles_light.qss',
        'dark': 'styles_dark.qss',
        'macos': 'styles_macos.qss'
    }
    
    def __init__(self, app):
        self.app = app
        self.resources_dir = os.path.join(os.path.dirname(__file__), 'resources')
        self.current_theme = 'macos'
    
    def load_style(self, theme_name: str = None):
        """Загружает стили из QSS файла"""
        if theme_name:
            self.current_theme = theme_name
        
        qss_file = self.THEMES.get(self.current_theme, 'styles_macos.qss')
        filepath = os.path.join(self.resources_dir, qss_file)
        
        if not os.path.exists(filepath):
            print(f"⚠️ Файл стилей не найден: {filepath}")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                style = f.read()
            
            self.app.setStyleSheet(style)
            print(f"✅ Загружены стили: {qss_file}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка загрузки стилей: {e}")
            return False
    
    def switch_theme(self, theme_name: str):
        """Переключение темы"""
        if theme_name in self.THEMES:
            self.load_style(theme_name)
            return True
        return False
    
    def reload_style(self):
        """Перезагрузка текущего файла стилей (для разработки)"""
        return self.load_style(self.current_theme)