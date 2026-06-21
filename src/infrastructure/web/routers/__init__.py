from .user_router import router as user_router
from .notebook_router import router as notebook_router
from .study_room_router import router as study_room_router
from .assessment_router import router as assessment_router

__all__ = ["user_router", "notebook_router", "study_room_router", "assessment_router"]
