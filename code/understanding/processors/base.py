from abc import ABC, abstractmethod
from typing import Optional
from code.context.models import UnifiedContext
from code.understanding.models import UnderstandingResult

class BaseProcessor(ABC):
    """Abstract base class that enforces the process signature for all semantic processors."""
    
    @abstractmethod
    def process(self, context: UnifiedContext) -> Optional[UnderstandingResult]:
        """Extracts semantic understanding from the UnifiedContext."""
        pass
