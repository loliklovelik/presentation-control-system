import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple


class DatabaseManager:
    """Менеджер базы данных для хранения статистики выступлений и аналитики речи"""

    def __init__(self, db_path: str = "presentation_stats.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Инициализация базы данных: создание всех таблиц если они не существуют"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 1. Таблица сценариев (пресетов)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Таблица этапов сценария
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS script_stages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    script_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    planned_duration_ms INTEGER NOT NULL,
                    stage_order INTEGER NOT NULL,
                    track_overtime BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE CASCADE
                )
            """)

            # 3. Основная таблица выступлений
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS presentations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    script_id INTEGER,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    timer_mode TEXT NOT NULL,
                    warning_threshold_sec INTEGER,
                    total_pause_count INTEGER DEFAULT 0,
                    total_pause_duration_ms INTEGER DEFAULT 0,
                    inter_stage_pause_ms INTEGER DEFAULT 0,
                    planned_duration_ms INTEGER,
                    actual_duration_ms INTEGER,
                    overtime_ms INTEGER DEFAULT 0,
                    FOREIGN KEY (script_id) REFERENCES scripts(id)
                )
            """)

            # 4. Таблица деталей выступления по этапам
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS presentation_stages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    presentation_id INTEGER NOT NULL,
                    script_stage_id INTEGER,
                    stage_name TEXT NOT NULL,
                    planned_duration_ms INTEGER,
                    actual_duration_ms INTEGER NOT NULL,
                    overtime_ms INTEGER DEFAULT 0,
                    pause_count INTEGER DEFAULT 0,
                    pause_duration_ms INTEGER DEFAULT 0,
                    FOREIGN KEY (presentation_id) REFERENCES presentations(id) ON DELETE CASCADE,
                    FOREIGN KEY (script_stage_id) REFERENCES script_stages(id)
                )
            """)

            # 5. Таблица аналитики речи
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS speech_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    presentation_id INTEGER NOT NULL UNIQUE,
                    total_words INTEGER,
                    speech_duration_sec INTEGER,
                    avg_speed_wpm REAL,
                    min_speed_wpm REAL,
                    max_speed_wpm REAL,
                    long_pause_count INTEGER,
                    filler_word_count INTEGER,
                    monotony_score REAL,
                    speed_data_points TEXT,
                    pause_data_points TEXT,
                    FOREIGN KEY (presentation_id) REFERENCES presentations(id) ON DELETE CASCADE
                )
            """)

            # 6. Таблица для хранения временных меток пауз (детализация)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pause_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    presentation_id INTEGER NOT NULL,
                    pause_start_sec REAL,
                    pause_duration_sec REAL,
                    FOREIGN KEY (presentation_id) REFERENCES presentations(id) ON DELETE CASCADE
                )
            """)

            # Миграция: добавляем колонки, если их ещё нет
            try:
                cursor.execute("ALTER TABLE presentations ADD COLUMN inter_stage_pause_ms INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # колонка уже существует

            try:
                cursor.execute("ALTER TABLE presentation_stages ADD COLUMN pause_count INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

            try:
                cursor.execute("ALTER TABLE presentation_stages ADD COLUMN pause_duration_ms INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

            # Создаем индексы
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_presentations_date ON presentations(start_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_presentations_script ON presentations(script_id)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_speech_analytics_presentation ON speech_analytics(presentation_id)")

            conn.commit()

    # ==================== РАБОТА СО СЦЕНАРИЯМИ ====================

    def add_script(self, name: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO scripts (name) VALUES (?)",
                (name,)
            )
            conn.commit()
            cursor.execute("SELECT id FROM scripts WHERE name = ?", (name,))
            result = cursor.fetchone()
            return result[0] if result else -1

    def add_script_stage(self, script_id: int, name: str, duration_ms: int,
                         stage_order: int, track_overtime: bool = True) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO script_stages 
                (script_id, name, planned_duration_ms, stage_order, track_overtime)
                VALUES (?, ?, ?, ?, ?)
            """, (script_id, name, duration_ms, stage_order, track_overtime))
            conn.commit()
            return cursor.lastrowid

    def get_script_with_stages(self, script_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scripts WHERE id = ?", (script_id,))
            script = cursor.fetchone()
            if not script:
                return None
            cursor.execute("""
                SELECT * FROM script_stages 
                WHERE script_id = ? 
                ORDER BY stage_order
            """, (script_id,))
            stages = [dict(row) for row in cursor.fetchall()]
            result = dict(script)
            result['stages'] = stages
            return result

    def get_all_scripts(self) -> List[Tuple[int, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM scripts ORDER BY name")
            return cursor.fetchall()

    def delete_script(self, script_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scripts WHERE id = ?", (script_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ==================== РАБОТА С ВЫСТУПЛЕНИЯМИ ====================

    def add_presentation(self, stats: Dict[str, Any]) -> int:
        """
        Сохраняет основную запись о выступлении

        Args:
            stats: Словарь со статистикой выступления из TimerEngine

        Returns:
            ID записи выступления
        """
        with sqlite3.connect(self.db_path, timeout=5) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO presentations
                (script_id, start_time, end_time, timer_mode, 
                 warning_threshold_sec, total_pause_count, total_pause_duration_ms,
                 inter_stage_pause_ms, planned_duration_ms, actual_duration_ms, overtime_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stats.get('script_id'),
                stats.get('start_timestamp', datetime.now().isoformat()),
                stats.get('end_timestamp', datetime.now().isoformat()),
                stats.get('mode', 'countdown'),
                stats.get('warning_threshold_sec', 60),
                stats.get('pause_count', 0),
                stats.get('total_pause_ms', 0),
                stats.get('inter_stage_pause_ms', 0),
                stats.get('planned_duration_ms'),
                stats.get('actual_duration_ms'),
                stats.get('overtime_ms', 0)
            ))
            presentation_id = cursor.lastrowid

            # Сохраняем этапы в той же транзакции
            if 'stages' in stats and stats['stages']:
                for stage in stats['stages']:
                    cursor.execute("""
                        INSERT INTO presentation_stages
                        (presentation_id, script_stage_id, stage_name, 
                         planned_duration_ms, actual_duration_ms, overtime_ms,
                         pause_count, pause_duration_ms)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        presentation_id,
                        stage.get('script_stage_id'),
                        stage.get('stage_name', 'Этап'),
                        stage.get('planned_duration_ms'),
                        stage.get('actual_duration_ms', 0),
                        stage.get('overtime_ms', 0),
                        stage.get('pause_count', 0),
                        stage.get('pause_duration_ms', 0)
                    ))

            # Сохраняем паузы в той же транзакции
            if 'pause_details' in stats and stats['pause_details']:
                for pause in stats['pause_details']:
                    cursor.execute("""
                        INSERT INTO pause_details
                        (presentation_id, pause_start_sec, pause_duration_sec)
                        VALUES (?, ?, ?)
                    """, (
                        presentation_id,
                        pause.get('start_sec', 0),
                        pause.get('duration_sec', 0)
                    ))

            conn.commit()
            return presentation_id

    def get_presentation_stats(self, presentation_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, sc.name as script_name
                FROM presentations p
                LEFT JOIN scripts sc ON p.script_id = sc.id
                WHERE p.id = ?
            """, (presentation_id,))
            presentation = cursor.fetchone()
            if not presentation:
                return None
            result = dict(presentation)
            cursor.execute("""
                SELECT * FROM presentation_stages 
                WHERE presentation_id = ? 
                ORDER BY id
            """, (presentation_id,))
            result['stages'] = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT * FROM speech_analytics WHERE presentation_id = ?", (presentation_id,))
            analytics = cursor.fetchone()
            if analytics:
                result['speech_analytics'] = dict(analytics)
                if result['speech_analytics'].get('speed_data_points'):
                    result['speech_analytics']['speed_data_points'] = json.loads(
                        result['speech_analytics']['speed_data_points']
                    )
                if result['speech_analytics'].get('pause_data_points'):
                    result['speech_analytics']['pause_data_points'] = json.loads(
                        result['speech_analytics']['pause_data_points']
                    )
            cursor.execute("""
                SELECT * FROM pause_details 
                WHERE presentation_id = ? 
                ORDER BY pause_start_sec
            """, (presentation_id,))
            result['pauses'] = [dict(row) for row in cursor.fetchall()]
            return result

    def get_all_presentations(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.id, 
                    p.start_time,
                    p.end_time,
                    p.timer_mode,
                    p.total_pause_count,
                    p.total_pause_duration_ms,
                    p.inter_stage_pause_ms,
                    p.planned_duration_ms,
                    p.actual_duration_ms,
                    p.overtime_ms,
                    sc.name as script_name,
                    sa.avg_speed_wpm,
                    sa.filler_word_count
                FROM presentations p
                LEFT JOIN scripts sc ON p.script_id = sc.id
                LEFT JOIN speech_analytics sa ON p.id = sa.presentation_id
                ORDER BY p.start_time DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def get_presentations_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.id, 
                    p.start_time,
                    p.end_time,
                    p.timer_mode,
                    p.planned_duration_ms,
                    p.actual_duration_ms,
                    p.overtime_ms,
                    sc.name as script_name
                FROM presentations p
                LEFT JOIN scripts sc ON p.script_id = sc.id
                WHERE date(p.start_time) >= ? AND date(p.start_time) <= ?
                ORDER BY p.start_time DESC
            """, (start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]

    # ==================== АНАЛИТИКА РЕЧИ ====================

    def add_speech_analytics(self, presentation_id: int, analytics: Dict[str, Any]) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            speed_points = analytics.get('speed_data_points')
            pause_points = analytics.get('pause_data_points')
            speed_json = json.dumps(speed_points) if speed_points else None
            pause_json = json.dumps(pause_points) if pause_points else None
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO speech_analytics
                    (presentation_id, total_words, speech_duration_sec,
                     avg_speed_wpm, min_speed_wpm, max_speed_wpm,
                     long_pause_count, filler_word_count, monotony_score,
                     speed_data_points, pause_data_points)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    presentation_id,
                    analytics.get('total_words', 0),
                    analytics.get('speech_duration_sec', 0),
                    analytics.get('avg_speed_wpm', 0.0),
                    analytics.get('min_speed_wpm', 0.0),
                    analytics.get('max_speed_wpm', 0.0),
                    analytics.get('long_pause_count', 0),
                    analytics.get('filler_word_count', 0),
                    analytics.get('monotony_score', 0.0),
                    speed_json,
                    pause_json
                ))
                conn.commit()
                return True
            except sqlite3.Error as e:
                print(f"Ошибка сохранения аналитики речи: {e}")
                return False

    # ==================== СТАТИСТИКА ====================

    def get_statistics_summary(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_presentations,
                    AVG(actual_duration_ms) / 1000.0 / 60.0 as avg_duration_min,
                    SUM(total_pause_count) as total_pauses,
                    AVG(total_pause_duration_ms) / 1000.0 as avg_pause_sec,
                    SUM(CASE WHEN overtime_ms > 0 THEN 1 ELSE 0 END) as overtime_count,
                    AVG(overtime_ms) / 1000.0 as avg_overtime_sec
                FROM presentations
            """)
            result = cursor.fetchone()
            return {
                'total_presentations': result[0] or 0,
                'avg_duration_min': round(result[1] or 0, 2),
                'total_pauses': result[2] or 0,
                'avg_pause_sec': round(result[3] or 0, 2),
                'overtime_count': result[4] or 0,
                'avg_overtime_sec': round(result[5] or 0, 2)
            }

    def export_to_json(self, output_path: str = None) -> str:
        if not output_path:
            output_path = f"db_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        all_data = {
            'scripts': [],
            'presentations': []
        }
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Явно указываем колонки БЕЗ description
            cursor.execute("SELECT id, name, created_at FROM scripts")
            all_data['scripts'] = [dict(row) for row in cursor.fetchall()]

            # Получаем все выступления
            presentations = self.get_all_presentations(limit=10000)
            for pres in presentations:
                full_pres = self.get_presentation_stats(pres['id'])
                if full_pres:
                    # Удаляем notes если он есть (для старых БД)
                    full_pres.pop('notes', None)
                    all_data['presentations'].append(full_pres)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)
        return output_path

    def get_db_info(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            info = {}
            tables = ['scripts', 'presentations', 'speech_analytics']
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                info[table] = cursor.fetchone()[0]
            return info

    def vacuum(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("VACUUM")