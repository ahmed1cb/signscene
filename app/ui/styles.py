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

/* ---------- Cards / panels ---------- */
#Card {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

    /* ---------- Top bar / window titlebar ---------- */
    #TitleBar {{
        background-color: {PANEL};
        border-bottom: 1px solid {BORDER};
    }}

    #TitleBar QLabel {{
        background: transparent;
    }}

    #Brand {{
        font-size: 15px;
        font-weight: 700;
        color: {TEXT};
    }}

    #WindowButton {{
        background-color: transparent;
        border: none;
        border-radius: 6px;
        color: {TEXT_MUTED};
        font-size: 15px;
        font-weight: 600;
        padding: 0;
    }}

    #WindowButton:hover {{
        background-color: {PANEL_ALT};
        color: {TEXT};
    }}

    #WindowButton:pressed {{
        background-color: {BORDER};
        color: {TEXT};
    }}

    #WindowCloseButton {{
        background-color: transparent;
        border: none;
        border-radius: 6px;
        color: {TEXT_MUTED};
        font-size: 15px;
        font-weight: 600;
        padding: 0;
    }}

    #WindowCloseButton:hover {{
        background-color: {ERROR};
        color: {TEXT};
    }}

    #WindowCloseButton:pressed {{
        background-color: #E25555;
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

#GhostButton:disabled {{
    background: transparent;
    border: 1px solid {BORDER};
    color: {TEXT_MUTED};
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

    /* ---------- Scenes / messages split ---------- */
    #SceneSplitter,
    #MainMessagesSplitter {{
        background: transparent;
    }}

    #SceneSplitter::handle,
    #MainMessagesSplitter::handle {{
        background: transparent;
    }}

    #MainMessagesSplitter::handle:vertical {{
        height: 8px;
    }}

    #MainMessagesSplitter::handle:vertical:hover,
    #MainMessagesSplitter::handle:vertical:pressed {{
        background-color: {BORDER};
        border-radius: 3px;
    }}

    #SceneSplitter::handle:horizontal {{
        width: 8px;
    }}

    #SceneSplitter::handle:horizontal:hover,
    #SceneSplitter::handle:horizontal:pressed {{
        background-color: {BORDER};
        border-radius: 3px;
    }}

#ScenePreview {{
    background-color: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
}}

/* ---------- Incoming call / danger actions ---------- */
#IncomingCallBar {{
    background-color: {ACCENT_SOFT};
    border: 1px solid {ACCENT};
    border-radius: 10px;
}}

#IncomingCallLabel {{
    color: {TEXT};
    font-size: 13px;
    font-weight: 600;
}}

#DangerButton {{
    background-color: {ERROR};
    color: {TEXT};
}}

#DangerButton:hover {{
    background-color: #FF8585;
}}

#DangerButton:pressed {{
    background-color: #E25555;
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

"""
