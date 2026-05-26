def ms_to_time_str(ms: int) -> str:
    """Преобразует миллисекунды в строку ММ:СС"""
    if ms < 0:
        ms = abs(ms)
    seconds = ms // 1000
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def time_str_to_ms(time_str: str) -> int:
    """Преобразует строку ММ:СС в миллисекунды"""
    try:
        if ':' in time_str:
            parts = time_str.split(':')
            minutes = int(parts[0]) if parts[0] else 0
            seconds = int(parts[1]) if parts[1] else 0
        else:
            minutes = int(time_str) if time_str else 0
            seconds = 0
        return (minutes * 60 + seconds) * 1000
    except:
        return 300000  # 5 минут по умолчанию


def validate_time_input(text: str) -> bool:
    """Проверяет корректность ввода времени"""
    if not text:
        return False

    # Разрешаем ввод без двоеточия (только минуты)
    if ':' not in text:
        try:
            minutes = int(text)
            return 0 <= minutes <= 99
        except:
            return False

    # Проверяем формат с двоеточием
    parts = text.split(':')
    if len(parts) != 2:
        return False

    try:
        minutes = int(parts[0]) if parts[0] else 0
        seconds = int(parts[1]) if parts[1] else 0
        return 0 <= minutes <= 99 and 0 <= seconds <= 59
    except:
        return False