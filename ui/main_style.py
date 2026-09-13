MAIN_STYLE = """
QMainWindow {
    background-color: #ECF0F1;
}
QLabel {
    color: #2C3E50;
}
#displayFrame {
    background-color: #FFFFFF;
    border-radius: 15px;
    border: 2px solid #BDC3C7;
}
#timerLabel {
    background-color: #2E7D32;
    color: white;
    border-radius: 10px;
}
"""

SECONDARY_TIMER_LABEL = """
#secondaryTimerLabel {
    color: #2C3E50;
    background-color: transparent;
    font-weight: bold;
}
"""

PAUSE_STATS_LABEL = """
QLabel {
    color: #7F8C8D;
    font-size: 14px;
    padding: 3px;
    background-color: transparent;
}
"""

INPUT_LABEL = """
QLabel {
    background-color: transparent;
    color: #2C3E50;
    font-weight: bold;
    border: none;
}
"""

TIME_INPUT = """
QLineEdit {
    background-color: #FFFFFF;
    color: #000000;
    border: 2px solid #3498DB;
    border-radius: 6px;
    font-weight: bold;
    selection-background-color: #3498DB;
    selection-color: #FFFFFF;
    padding: 5px;
}
QLineEdit:focus {
    border-color: #2980B9;
    background-color: #FFFFFF;
}
QLineEdit:disabled {
    background-color: #F0F0F0;
    color: #7F8C8D;
}
"""