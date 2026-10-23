ACCENT = "#FFB703"
ACCENT_HOVER = "#FFC533"
ACCENT_ACTIVE = "#D99C00"
ACCENT_SOFT = "#2B2410"
ACCENT_TEXT = "#0B1330"

BG = "#0B1330"
PANEL = "#111D40"
PANEL_ALT = "#182A55"
BORDER = "#263A6B"
BORDER_FOCUS = ACCENT

TEXT = "#F4F7FF"
TEXT_MUTED = "#9CABCF"
ERROR = "#FF6B6B"
SUCCESS = "#4DD0D4"

APP_STYLESHEET = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-size: 14px;
}}

QMainWindow {{
    background-color: {BG};
}}

/* ---------- Cards / panels ---------- */
#Card {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

/* ---------- Top bar ---------- */
#TopBar {{
    background-color: {PANEL};
    border-bottom: 1px solid {BORDER};
}}

#Brand {{
    font-size: 18px;
    font-weight: 700;
    color: {TEXT};
}}

/* ---------- Headings ---------- */
#Title {{
    font-size: 26px;
    font-weight: 700;
    color: {TEXT};
}}

#Subtitle {{
    font-size: 13px;
    color: {TEXT_MUTED};
}}

/* ---------- Form fields ---------- */
QLineEdit {{
    background-color: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px 12px;
    color: {TEXT};
    selection-background-color: {ACCENT};
    selection-color: {ACCENT_TEXT};
}}

QLineEdit:focus {{
    border: 1px solid {BORDER_FOCUS};
}}

QLineEdit[invalid="true"] {{
    border: 1px solid {ERROR};
}}

QLineEdit[valid="true"] {{
    border: 1px solid {SUCCESS};
}}

QLineEdit:disabled {{
    color: {TEXT_MUTED};
}}

/* ---------- Buttons ---------- */
QPushButton {{
    background-color: {ACCENT};
    color: {ACCENT_TEXT};
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {ACCENT_HOVER};
}}

QPushButton:pressed {{
    background-color: {ACCENT_ACTIVE};
}}

QPushButton:disabled {{
    background-color: {PANEL_ALT};
    color: {TEXT_MUTED};
}}

#LinkButton {{
    background: transparent;
    color: {ACCENT};
    border: none;
    font-weight: 500;
    padding: 4px;
}}

#LinkButton:hover {{
    color: {ACCENT_HOVER};
    background: transparent;
    text-decoration: underline;
}}

#GhostButton {{
    background-color: transparent;
    border: 1px solid {BORDER};
    color: {TEXT};
}}

#GhostButton:hover {{
    background-color: {PANEL_ALT};
    border: 1px solid {ACCENT};
}}

/* ---------- Labels ---------- */
QLabel {{
    background: transparent;
}}

#CameraVideo {{
    background-color: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {TEXT_MUTED};
    font-size: 12px;
}}

#CameraHud {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}

#ComposingLabel {{
    color: {TEXT};
    font-size: 16px;
    font-weight: 600;
    padding: 4px;
}}

#GestureLabel {{
    color: {SUCCESS};
    font-size: 15px;
    font-weight: 700;
    padding: 2px;
}}

QFrame#Card[recognized="true"] {{
    border: 2px solid {ACCENT};
    background-color: {ACCENT_SOFT};
}}

/* ---------- Message bubbles ---------- */
#MessageScroll {{
    background: transparent;
    border: none;
}}

#BubbleMine {{
    background-color: {ACCENT_SOFT};
    border: 1px solid {ACCENT};
    border-radius: 10px;
    padding: 8px 12px;
    color: {TEXT};
    font-size: 13px;
}}

#BubbleTheirs {{
    background-color: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 8px 12px;
    color: {TEXT};
    font-size: 13px;
}}

#Hint {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}

#StatusDot {{
    color: {SUCCESS};
    font-size: 12px;
}}

#ErrorLabel {{
    color: {ERROR};
    font-size: 12px;
}}

#SuccessLabel {{
    color: {SUCCESS};
    font-size: 12px;
}}

/* ---------- Checkboxes ---------- */
QCheckBox {{
    spacing: 8px;
    color: {TEXT};
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background-color: {PANEL_ALT};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border: 1px solid {ACCENT};
}}

/* ---------- Password toggle button ---------- */
#TogglePassword {{
    background: transparent;
    border: none;
    color: {TEXT_MUTED};
    padding: 0 6px;
    font-weight: 400;
}}

#TogglePassword:hover {{
    color: {TEXT};
    background: transparent;
}}

/* ---------- Voice / audio controls ---------- */
QComboBox {{
    background-color: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    color: {TEXT};
}}

QComboBox:hover {{
    border: 1px solid {ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 22px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {TEXT_MUTED};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {PANEL_ALT};
    border: 1px solid {BORDER};
    color: {TEXT};
    selection-background-color: {ACCENT};
    selection-color: {ACCENT_TEXT};
    outline: none;
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}

QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {TEXT};
    border: 1px solid {ACCENT};
    width: 12px;
    height: 12px;
    margin: -5px 0;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background: {ACCENT};
}}
"""
