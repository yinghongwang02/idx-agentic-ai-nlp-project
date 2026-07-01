from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    name: str

    @abstractmethod
    def run(self, input_data: Any) -> Any:
        raise NotImplementedError