from app.services.base import CRUDBase
from app.models.element import PageElement
from app.schemas.element import PageElementCreate, PageElementUpdate

class ElementService(CRUDBase[PageElement, PageElementCreate, PageElementUpdate]):
    pass

element_service = ElementService(PageElement)
