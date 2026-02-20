from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtCore import Qt

class ThemeColors:
    def __init__(self, bg, text, card_bg, card_text, accent, shadow, focus_border):
        self.bg = bg
        self.text = text
        self.card_bg = card_bg
        self.card_text = card_text
        self.accent = accent
        self.shadow = shadow
        self.focus_border = focus_border

LIGHT_THEME = ThemeColors(
    bg="#F2F3F5",             # ニュートラルグレー
    text="#333333",           # 濃いグレー
    card_bg="#FFFFFF",        # 白
    card_text="#222222",      # ほぼ黒
    accent="#4A90E2",         # 青（差し色統一）
    shadow="rgba(0, 0, 0, 30)", # 薄い影（Alpha 30）
    focus_border="#4A90E2"
)

DARK_THEME = ThemeColors(
    bg="#101010",             # 非常に濃いグレー
    text="#E0E0E0",           # 明るいグレー
    card_bg="#1E1E1E",        # Surface color
    card_text="#FFFFFF",      # 白
    accent="#4A90E2",         # 青（差し色統一）
    shadow="rgba(0, 0, 0, 80)", # 少し濃い影（背景が暗いので調整）
    focus_border="#4A90E2"
)

class ThemeManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
            cls._instance.is_dark = False
            cls._instance.current_theme = LIGHT_THEME
        return cls._instance

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.current_theme = DARK_THEME if self.is_dark else LIGHT_THEME
    
    def get_style_sheet(self):
        t = self.current_theme
        hover_bg = "#FAFAFA" if not self.is_dark else "#252525"
        
        # タイトル描画用の左バー色はここで定義
        section_title_style = f"""
            QLabel#SectionTitle {{
                font-size: 28px;
                font-weight: bold;
                padding-left: 12px;
                border: none;
                border-left: 8px solid {t.accent};
                color: {t.text};
                background-color: transparent;
            }}
        """

        return f"""
            QWidget {{
                background-color: {t.bg};
                color: {t.text};
                font-family: "Segoe UI", sans-serif;
            }}
            QLabel {{
                background-color: transparent;
                color: {t.text};
                border: none;
            }}
            /* セクションタイトル（左バー付き） */
            {section_title_style}

            QFrame#TaskCard {{
                background-color: {t.card_bg};
                border-radius: 14px;
                border: 2px solid transparent;
                padding: 16px;
            }}
            QFrame#TaskCard:hover {{
                background-color: {hover_bg};
            }}
            QFrame#TaskCard[is_focus="true"] {{
                border: 2px solid {t.focus_border};
            }}
            QLabel#TaskTitle {{
                font-size: 22px;
                font-weight: bold;
                color: {t.card_text};
                border: none;
            }}
            QLabel#TaskDesc {{
                font-size: 16px;
                color: {t.text};
                opacity: 0.8;
                border: none;
            }}
            /* Focused Task Styles */
            QLabel#TaskTitle[is_focus="true"] {{
                font-size: 26px;
            }}
            QLabel#TaskDesc[is_focus="true"] {{
                font-size: 18px;
            }}
            QPushButton {{
                background-color: {t.card_bg};
                color: {t.text};
                border: 1px solid {t.text};
                border-radius: 8px;
                padding: 8px;
                font-size: 18px;
            }}
            QPushButton:pressed {{
                background-color: {t.accent};
                color: {t.bg};
            }}
            
            /* 完了パネル */
            QFrame#HistoryPanel {{
                background-color: {t.card_bg if self.is_dark else "#F2F3F5"}; /* パネル自体の背景（ライト時はグレー） */
                border-top-left-radius: 20px;
                border-bottom-left-radius: 20px;
            }}
            QFrame#CompletedCard {{
                background-color: {t.card_bg if self.is_dark else "#FFFFFF"};
                border-radius: 12px;
                border: 2px solid {t.accent};
                padding: 14px;
            }}
        """

    def get_palette(self):
        t = self.current_theme
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(t.bg))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(t.text))
        palette.setColor(QPalette.ColorRole.Base, QColor(t.card_bg))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(t.bg))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(t.text))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(t.bg))
        palette.setColor(QPalette.ColorRole.Text, QColor(t.text))
        palette.setColor(QPalette.ColorRole.Button, QColor(t.card_bg))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(t.card_text))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(t.accent))
        palette.setColor(QPalette.ColorRole.Link, QColor(t.accent))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(t.accent))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(t.bg))
        return palette
