"""
UI Theme and Stylesheet for USV Ground Station.
Follows a clean, dark macOS / Shadcn-inspired aesthetic.
"""

STYLESHEET = """
QMainWindow {
    background: #09090b;
    color: #fafafa;
}
QWidget {
    font-family: "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    color: #fafafa;
}

/* Menu Bar */
QMenuBar {
    background: #09090b;
    color: #a1a1aa;
    border-bottom: 1px solid #18181b;
    padding: 2px 6px;
    font-size: 13px;
}
QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background: #27272a;
    color: #fafafa;
}
QMenu {
    background: #18181b;
    border: 1px solid #27272a;
    border-radius: 8px;
    padding: 4px;
    color: #fafafa;
    font-size: 13px;
}
QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #27272a;
    color: #38bdf8;
}
QMenu::separator {
    height: 1px;
    background: #27272a;
    margin: 4px 8px;
}

/* Combo Box & Dropdown Menus */
QComboBox {
    background: #18181b;
    border: 1px solid #27272a;
    border-radius: 5px;
    padding: 3px 8px;
    color: #fafafa;
    font-size: 11px;
    font-weight: 500;
}
QComboBox:hover {
    border-color: #3f3f46;
}
QComboBox:focus {
    border-color: #38bdf8;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 18px;
    border-left: none;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #a1a1aa;
    width: 0px;
    height: 0px;
    margin-right: 6px;
}
QComboBox::down-arrow:hover {
    border-top-color: #38bdf8;
}

/* Dropdown Popup List View (Prevents White-on-White Clipping/Glitch) */
QComboBox QAbstractItemView {
    background-color: #18181b;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    color: #f4f4f5;
    selection-background-color: #27272a;
    selection-color: #38bdf8;
    padding: 3px;
    outline: none;
    min-width: 140px;
}
QComboBox QAbstractItemView::item {
    min-height: 24px;
    padding: 3px 10px;
    color: #f4f4f5;
    background-color: transparent;
    border-radius: 4px;
}
QComboBox QAbstractItemView::item:hover,
QComboBox QAbstractItemView::item:selected {
    background-color: #27272a;
    color: #38bdf8;
}

/* Table */
QTableWidget {
    background: #09090b;
    border: 1px solid #27272a;
    border-radius: 6px;
    gridline-color: transparent;
    color: #e4e4e7;
    selection-background-color: #1e293b;
    selection-color: #38bdf8;
    font-size: 11px;
    outline: none;
}
QTableWidget::item {
    padding: 3px 6px;
    border: none;
}
QTableWidget::item:hover {
    background: #18181b;
}
QHeaderView::section {
    background: #0c0c0e;
    color: #71717a;
    padding: 5px 6px;
    border: none;
    border-bottom: 1px solid #27272a;
    font-weight: 600;
    font-size: 10px;
}

/* Global Modern Scrollbars */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #27272a;
    min-height: 20px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background: #3f3f46;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* Slider */
QSlider::groove:horizontal {
    height: 4px;
    background: #27272a;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #38bdf8;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #fafafa;
    border: 1px solid #71717a;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #ffffff;
    border-color: #38bdf8;
}

/* Console */
QTextEdit {
    background: #09090b;
    border: 1px solid #27272a;
    border-radius: 4px;
    color: #a1a1aa;
    font-family: Menlo, Monaco, "SF Mono", monospace;
    font-size: 11px;
    padding: 6px;
}

/* Status Bar */
QStatusBar {
    background: #09090b;
    border-top: 1px solid #1c1c1f;
    min-height: 24px;
    max-height: 28px;
}
QStatusBar::item {
    border: none;
}

/* Resizable Splitter Handle */
QSplitter::handle:horizontal {
    background: #1c1c1f;
    width: 3px;
}
QSplitter::handle:horizontal:hover {
    background: #38bdf8;
    width: 4px;
}

/* Scroll Areas and Viewports */
QScrollArea {
    background-color: #0c0c0e;
    background: #0c0c0e;
    border: none;
}
QScrollArea > QWidget {
    background-color: #0c0c0e;
    background: #0c0c0e;
}
QScrollArea > QWidget > QWidget {
    background-color: #0c0c0e;
    background: #0c0c0e;
}
"""

STATUS_COLORS = {
    'FORMATION': '#38bdf8',
    'RTH': '#34d399',
    'ESTOP': '#f87171',
    'HOLD': '#fbbf24',
    'IDLE': '#71717a',
}
