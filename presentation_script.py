from typing import List, Optional

class PresentationStage:
    """Один этап выступления"""

    def __init__(self, name: str = "Этап", duration_ms: int = 300000):
        self.name = name  # например, "Доклад"
        self.duration_ms = duration_ms
        self.actual_duration_ms = 0  # будет заполнено после выступления

    def to_dict(self) -> dict:
        """Сериализация в словарь для сохранения"""
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "actual_duration_ms": self.actual_duration_ms
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PresentationStage':
        """Десериализация из словаря"""
        stage = cls(data["name"], data["duration_ms"])
        stage.actual_duration_ms = data.get("actual_duration_ms", 0)
        return stage

    def get_duration_str(self) -> str:
        """Возвращает длительность в формате ММ:СС"""
        seconds = self.duration_ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


class PresentationScript:
    """Сценарий выступления (последовательность этапов)"""

    def __init__(self, name: str = "Новый сценарий"):
        self.name = name
        self.stages: List[PresentationStage] = []
        self.current_stage_index = -1  # -1 значит не запущен
        self.total_duration_ms = 0

    def add_stage(self, stage: PresentationStage):
        """Добавить этап в конец списка"""
        self.stages.append(stage)
        self._update_total_duration()

    def insert_stage(self, index: int, stage: PresentationStage):
        """Вставить этап на указанную позицию"""
        self.stages.insert(index, stage)
        self._update_total_duration()

    def remove_stage(self, index: int) -> Optional[PresentationStage]:
        """Удалить этап по индексу"""
        if 0 <= index < len(self.stages):
            stage = self.stages.pop(index)
            self._update_total_duration()
            return stage
        return None

    def move_stage_up(self, index: int) -> bool:
        """Переместить этап выше. Возвращает True если успешно"""
        if index > 0 and index < len(self.stages):
            self.stages[index], self.stages[index - 1] = self.stages[index - 1], self.stages[index]
            return True
        return False

    def move_stage_down(self, index: int) -> bool:
        """Переместить этап ниже. Возвращает True если успешно"""
        if 0 <= index < len(self.stages) - 1:
            self.stages[index], self.stages[index + 1] = self.stages[index + 1], self.stages[index]
            return True
        return False

    def _update_total_duration(self):
        """Обновить общую длительность сценария"""
        self.total_duration_ms = sum(stage.duration_ms for stage in self.stages)

    def get_current_stage(self) -> Optional[PresentationStage]:
        """Получить текущий этап"""
        if 0 <= self.current_stage_index < len(self.stages):
            return self.stages[self.current_stage_index]
        return None

    def next_stage(self) -> bool:
        """Перейти к следующему этапу. Возвращает True, если есть следующий этап"""
        if self.current_stage_index + 1 < len(self.stages):
            # Сохраняем фактическую длительность предыдущего этапа
            if self.current_stage_index >= 0:
                # Эта логика будет обновляться из TimerEngine
                pass
            self.current_stage_index += 1
            return True
        return False

    def start(self) -> bool:
        """Запустить первый этап. Возвращает True если есть этапы"""
        if self.stages:
            self.current_stage_index = 0
            return True
        return False

    def reset(self):
        """Сбросить сценарий"""
        self.current_stage_index = -1
        for stage in self.stages:
            stage.actual_duration_ms = 0

    def is_finished(self) -> bool:
        """Проверить, завершен ли сценарий"""
        return self.current_stage_index >= len(self.stages) - 1

    def get_total_duration_str(self) -> str:
        """Возвращает общую длительность в формате ММ:СС"""
        seconds = self.total_duration_ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def to_dict(self) -> dict:
        """Сериализация в словарь для сохранения"""
        return {
            "name": self.name,
            "stages": [stage.to_dict() for stage in self.stages]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PresentationScript':
        """Десериализация из словаря"""
        script = cls(data["name"])
        for stage_data in data["stages"]:
            script.stages.append(PresentationStage.from_dict(stage_data))
        script._update_total_duration()
        return script

    def __len__(self) -> int:
        return len(self.stages)