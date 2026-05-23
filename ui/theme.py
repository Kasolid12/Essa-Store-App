# app_essa/ui/theme.py

class Theme:
    # --- CYBERPUNK INDUSTRIAL PALETTE ---
    BG_VOID = "#090A0F"       # Deepest black/grey for main window background
    BG_PANEL = "#161925"      # Dark slate for blocked grid panels
    TEXT_MAIN = "#E0E0E0"     # High-visibility ash white
    TEXT_MUTED = "#8B93A5"    # Dimmed grey for labels/placeholders
    
    # Neon Accents
    NEON_CYAN = "#00F0FF"     # Primary action color (Cyberpunk Blue)
    NEON_PINK = "#FF003C"     # Danger/Delete action color
    NEON_YELLOW = "#FCE205"   # Warnings/Pending status
    BORDER_DIM = "#2A2E45"    # Gridline color
    
    # --- GLOBAL STYLESHEET (QSS) ---
    GLOBAL_STYLESHEET = f"""
        /* 1. APP BACKGROUND & FONT */
        QWidget {{
            background-color: {BG_VOID};
            color: {TEXT_MAIN};
            font-family: 'Segoe UI', 'Roboto', 'Consolas', sans-serif;
            font-size: 10pt;
        }}

        /* 2. COLOR-BLOCKED PANELS (No rounded corners!) */
        QFrame#GridPanel {{
            background-color: {BG_PANEL};
            border: 1px solid {BORDER_DIM};
            border-radius: 0px; 
        }}

        /* 3. SHARP NEON BUTTONS */
        QPushButton {{
            background-color: transparent;
            border: 1px solid {NEON_CYAN};
            color: {NEON_CYAN};
            padding: 8px 16px;
            font-weight: bold;
            font-size: 10pt;
            letter-spacing: 1px;
            text-transform: uppercase;
            border-radius: 0px;
        }}
        QPushButton:hover {{
            background-color: {NEON_CYAN};
            color: {BG_VOID};
        }}
        QPushButton:pressed {{
            background-color: #00C0CC; /* Slightly darker cyan */
            border: 1px solid #00C0CC;
        }}
        
        /* Danger Button Variant */
        QPushButton#BtnDanger {{
            border: 1px solid {NEON_PINK};
            color: {NEON_PINK};
        }}
        QPushButton#BtnDanger:hover {{
            background-color: {NEON_PINK};
            color: {BG_VOID};
        }}

        /* 4. INPUT FIELDS */
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            background-color: {BG_VOID};
            border: 1px solid {BORDER_DIM};
            color: {NEON_CYAN};
            padding: 6px;
            padding-right: 25px; /* Prevents text from hiding behind the buttons */
            border-radius: 0px;
            selection-background-color: {NEON_CYAN};
            selection-color: {BG_VOID};
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border: 1px solid {NEON_CYAN};
        }}

        /* Fix SpinBox Hitboxes & Custom Cyberpunk Arrows */
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 20px;
            border-left: 1px solid {BORDER_DIM};
            border-bottom: 1px solid {BORDER_DIM};
            background-color: {BG_PANEL};
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 20px;
            border-left: 1px solid {BORDER_DIM};
            background-color: {BG_PANEL};
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background-color: #1A3A4A;
        }}
        QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{
            background-color: {NEON_CYAN};
        }}

        /* Draw sharp triangle arrows using borders */
        QSpinBox::up-arrow {{
            image: none; 
            width: 0px; height: 0px;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid {NEON_CYAN};
        }}
        QSpinBox::down-arrow {{
            image: none;
            width: 0px; height: 0px;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {NEON_CYAN};
        }}
        /* Invert arrow color when clicked */
        QSpinBox::up-arrow:pressed {{ border-bottom: 5px solid {BG_VOID}; }}
        QSpinBox::down-arrow:pressed {{ border-top: 5px solid {BG_VOID}; }}
    """