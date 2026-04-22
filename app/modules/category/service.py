from fastapi import HTTPException, status
from app.modules.category.models import Category
from app.modules.category.schemas import (
    CategoryCreate,
    CategoryList,
    CategoryPublic,
    CategoryUpdate,
)
from sqlmodel import Session
from app.modules.category.unit_of_work import CategoryUnitOfWork
from datetime import datetime, timezone


class CategoryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(self, uow: CategoryUnitOfWork, category_id: int) -> Category:
        category = uow.categorias.get_by_id(category_id)
        if not category:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"Categoria id {category_id} no encontrada"
            )
        return category

    def _get_active_or_404(self, uow: CategoryUnitOfWork, category_id: int) -> Category:
        category = uow.categorias.get_by_id_active(category_id)
        if not category:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria no encontrada")
        return category

    def _assert_name_unique(self, uow: CategoryUnitOfWork, category_name: str):
        if uow.categorias.get_by_name(category_name.lower()):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"La categoria con nombre {category_name} ya existe",
            )

    def create(self, data: CategoryCreate) -> CategoryPublic:
        with CategoryUnitOfWork(self._session) as uow:
            self._assert_name_unique(uow, data.name)

            categoria = Category.model_validate(data)
            uow.categorias.add(categoria)
            result = CategoryPublic.model_validate(categoria)

        return result

    def get_by_id(self, category_id: int, only_actives: bool = True) -> CategoryPublic:
        with CategoryUnitOfWork(self._session) as uow:
            if only_actives:
                category = self._get_active_or_404(uow, category_id)
            else:
                category = self._get_or_404(uow, category_id)
            result = CategoryPublic.model_validate(category)
        return result

    def list_all(
        self, offset: int = 0, limit: int = 20, only_actives: bool = True
    ) -> CategoryList:
        with CategoryUnitOfWork(self._session) as uow:
            if only_actives:
                categories = uow.categorias.get_all_active(offset, limit)
                total = uow.categorias.count_active()
            else:
                categories = uow.categorias.get_all(offset, limit)
                total = uow.categorias.count()

        data = [CategoryPublic.model_validate(c) for c in categories]
        return CategoryList(data=data, total=total)

    def update(self, category_id: int, data: CategoryUpdate) -> CategoryPublic:
        with CategoryUnitOfWork(self._session) as uow:
            category = self._get_active_or_404(uow, category_id)
            if data.name and data.name != category.name:
                self._assert_name_unique(uow, data.name)

            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(category, field, value)
            category.updated_at = datetime.now(timezone.utc)
            uow.categorias.add(category)
            result = CategoryPublic.model_validate(category)
        return result

    def delete(self, category_id: int):
        with CategoryUnitOfWork(self._session) as uow:
            category = self._get_active_or_404(uow, category_id)
            uow.categorias.soft_delete(category)
        return status.HTTP_204_NO_CONTENT

    def search(self, query: str, offset: int = 0, limit: int = 20) -> CategoryList:
        if not query:
            return CategoryList(data=[], total=0)
        query = query.strip()
        with CategoryUnitOfWork(self._session) as uow:
            categorias = uow.categorias.search_by_name(query, offset, limit)
            total = uow.categorias.count_search_by_name(query)

        data = [CategoryPublic.model_validate(c) for c in categorias]

        return CategoryList(data=data, total=total)
