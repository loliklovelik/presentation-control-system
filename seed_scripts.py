"""Скрипт для заполнения БД популярными сценариями."""
from database_manager import DatabaseManager


def seed_scripts():
    db = DatabaseManager()

    scripts = [
        {
            "name": "Защита ВКР",
            "stages": [
                ("Доклад", 5, 0),
                ("Вопросы-ответы", 5, 0),
            ]
        },
        {
            "name": "Конференция",
            "stages": [
                ("Доклад", 10, 0),
                ("Вопросы", 5, 0)
            ]
        },
        {
            "name": "Лекция",
            "stages": [
                ("Введение", 10, 0),
                ("Основная часть", 35, 0),
                ("Перерыв", 10, 0),
                ("Обсуждение", 25, 0),
                ("Заключение", 10, 0)
            ]
        }
    ]

    for script_data in scripts:
        script_id = db.add_script(script_data["name"])
        if script_id == -1:
            print(f"⚠️ Сценарий «{script_data['name']}» уже существует, пропускаем")
            continue

        for i, (name, minutes, seconds) in enumerate(script_data["stages"]):
            duration_ms = (minutes * 60 + seconds) * 1000
            db.add_script_stage(script_id, name, duration_ms, i)

        print(f"✅ Сценарий «{script_data['name']}» добавлен (ID: {script_id})")

    print("\nГотово! Популярные сценарии добавлены в БД.")


if __name__ == "__main__":
    seed_scripts()