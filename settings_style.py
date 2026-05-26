SETTINGS_WINDOW_STYLE = """
    QWidget {
        background-color: #ECF0F1;
        color: #2C3E50;
        font-family: "Segoe UI", "Roboto", "Helvetica Neue", sans-serif;
        font-size: 13px;
    }
    QGroupBox {
        font-weight: bold;
        font-size: 14px;
        border: 2px solid #BDC3C7;
        border-radius: 8px;
        margin-top: 13px;
        padding-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
        top: -4px;
    }
    QCheckBox, QRadioButton {
        font-size: 13px;
        spacing: 5px;
    }
    QLabel {
        font-size: 13px;
    }
    QSpinBox {
        font-size: 13px;
        padding: 3px;
        border: 1px solid #BDC3C7;
        border-radius: 4px;
        background-color: white;
    }
    QPushButton {
        font-size: 13px;
        border: 1px solid #BDC3C7;
        border-radius: 4px;
        background-color: #F0F0F0;
        padding: 3px;
    }
"""

TITLE_LABEL_STYLE = """
    color: #2C3E50;
    font-size: 20px;
    font-weight: bold;
    background-color: transparent;
    font-family: "Segoe UI", "Roboto", "Helvetica Neue", sans-serif;
"""

COLOR_LABEL_STYLE = """
    font-weight: bold; 
    font-size: 13px;
"""

COLOR_BUTTON_STYLE = """
    background-color: {color};
    color: #2C3E50;
    border: 1px solid #2C3E50;
"""