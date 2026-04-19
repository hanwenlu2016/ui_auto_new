from app.services.base import CRUDBase
from app.models.element import PageElement
from app.models.page import Page
from app.schemas.element import PageElementCreate, PageElementUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Any, Dict, List
import json
import re

class ElementService(CRUDBase[PageElement, PageElementCreate, PageElementUpdate]):
    def _normalize_selector(self, selector: Any) -> str:
        return re.sub(r":visible\b", "", str(selector or "").strip(), flags=re.IGNORECASE)

    def _extract_selector_aliases(self, locator_value: Any, metadata_json: Any) -> List[str]:
        aliases: List[str] = []

        normalized = self._normalize_selector(locator_value)
        if normalized:
            aliases.append(normalized)

        metadata = metadata_json
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = None

        if isinstance(metadata, dict):
            locator_chain = metadata.get("locator_chain")
            if isinstance(locator_chain, dict):
                for raw in [
                    locator_chain.get("primary"),
                    locator_chain.get("fallback_1"),
                    locator_chain.get("fallback_2"),
                    locator_chain.get("fallback_3"),
                ]:
                    normalized = self._normalize_selector(raw)
                    if normalized:
                        aliases.append(normalized)
            elif isinstance(locator_chain, list):
                for raw in locator_chain:
                    normalized = self._normalize_selector(raw)
                    if normalized:
                        aliases.append(normalized)

            raw_aliases = metadata.get("selector_aliases")
            if isinstance(raw_aliases, list):
                for raw in raw_aliases:
                    normalized = self._normalize_selector(raw)
                    if normalized:
                        aliases.append(normalized)

        return list(dict.fromkeys(aliases))

    def _merge_metadata_json(
        self,
        existing_metadata: Any,
        incoming_metadata: Any,
        *,
        existing_locator_value: Any,
        incoming_locator_value: Any,
    ) -> Dict[str, Any]:
        existing = existing_metadata
        incoming = incoming_metadata

        if isinstance(existing, str):
            try:
                existing = json.loads(existing)
            except Exception:
                existing = {}
        if isinstance(incoming, str):
            try:
                incoming = json.loads(incoming)
            except Exception:
                incoming = {}

        existing = existing if isinstance(existing, dict) else {}
        incoming = incoming if isinstance(incoming, dict) else {}

        merged: Dict[str, Any] = {**existing, **incoming}
        merged_aliases = self._extract_selector_aliases(existing_locator_value, existing) + self._extract_selector_aliases(incoming_locator_value, incoming)
        if merged_aliases:
            merged["selector_aliases"] = list(dict.fromkeys(merged_aliases))
        return merged

    async def _find_existing_by_selector_alias(
        self,
        db: AsyncSession,
        *,
        page_id: int,
        locator_value: Any,
        metadata_json: Any,
    ) -> PageElement | None:
        incoming_aliases = set(self._extract_selector_aliases(locator_value, metadata_json))
        if not incoming_aliases:
            return None

        existing_elements = await self.get_multi(db, skip=0, limit=500, filters={"page_id": page_id})
        for element in existing_elements:
            existing_aliases = set(self._extract_selector_aliases(element.locator_value, element.metadata_json))
            if incoming_aliases & existing_aliases:
                return element
        return None

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, filters: dict = None
    ) -> List[PageElement]:
        query = select(self.model).options(
            selectinload(PageElement.creator),
            selectinload(PageElement.updater)
        )
        if filters:
            module_id = filters.pop("module_id", None)
            page_id = filters.pop("page_id", None)

            if module_id is not None:
                query = query.join(Page, Page.id == PageElement.page_id).where(Page.module_id == module_id)

            if page_id is not None:
                query = query.where(PageElement.page_id == page_id)

            for attr, value in filters.items():
                if hasattr(self.model, attr) and value is not None:
                    query = query.where(getattr(self.model, attr) == value)
        
        result = await db.execute(query.offset(skip).limit(limit))
        elements = result.scalars().all()
        
        for element in elements:
            if element.creator:
                element.creator_name = element.creator.full_name or element.creator.email
            if element.updater:
                element.updater_name = element.updater.full_name or element.updater.email
                
        return elements

    async def create(self, db: AsyncSession, *, obj_in: PageElementCreate, **kwargs) -> PageElement:
        obj_in_data = obj_in.model_dump()
        existing = await self._find_existing_by_selector_alias(
            db,
            page_id=obj_in_data["page_id"],
            locator_value=obj_in_data.get("locator_value"),
            metadata_json=obj_in_data.get("metadata_json"),
        )
        if not existing:
            return await super().create(db, obj_in=obj_in, **kwargs)

        update_data = {
            "name": existing.name or obj_in_data.get("name"),
            "description": existing.description or obj_in_data.get("description"),
            "locator_type": obj_in_data.get("locator_type") or existing.locator_type,
            "locator_value": obj_in_data.get("locator_value") or existing.locator_value,
            "metadata_json": self._merge_metadata_json(
                existing.metadata_json,
                obj_in_data.get("metadata_json"),
                existing_locator_value=existing.locator_value,
                incoming_locator_value=obj_in_data.get("locator_value"),
            ),
        }
        return await super().update(db, db_obj=existing, obj_in=update_data, **kwargs)

element_service = ElementService(PageElement)
