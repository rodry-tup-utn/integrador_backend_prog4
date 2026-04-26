from fastapi import HTTPException, status
from app.modules.category.models import Category
from app.modules.category.schemas import (
    CategoryCreate,
    CategoryList,
    CategoryPublic,
    CategoryUpdate,
    CategoryPublicTree,
    CategoryTree,
)
from sqlmodel import Session
from app.modules.category.unit_of_work import CategoryUnitOfWork
from datetime import datetime, timezone


class CategoryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # Helpers

    def _get_or_404(self, uow: CategoryUnitOfWork, category_id: int) -> Category:
        category = uow.categories.get_by_id(category_id)
        if not category:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Categoria id {category_id} no encontrada",
            )
        return category

    def _get_active_or_404(self, uow: CategoryUnitOfWork, category_id: int) -> Category:
        category = uow.categories.get_by_id_active(category_id)
        if not category:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "Categoria no encontrada",
            )
        return category

    def _assert_name_unique(self, uow: CategoryUnitOfWork, category_name: str):
        if uow.categories.get_by_name(category_name):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"La categoria con nombre {category_name} ya existe",
            )

    # Create

    def create(self, data: CategoryCreate) -> CategoryPublic:
        with CategoryUnitOfWork(self._session) as uow:
            self._assert_name_unique(uow, data.name)

            categoria = Category.model_validate(data)
            uow.categories.add(categoria)
            if data.parent_id:
                self._get_active_or_404(uow, data.parent_id)

            result = CategoryPublic.model_validate(categoria)
        return result

    # Get by id

    def get_by_id(self, category_id: int) -> CategoryPublic:
        with CategoryUnitOfWork(self._session) as uow:
            category = self._get_active_or_404(uow, category_id)
            result = CategoryPublic.model_validate(category)
        return result

    def get_by_id_admin(self, category_id: int) -> CategoryPublic:
        with CategoryUnitOfWork(self._session) as uow:
            category = self._get_or_404(uow, category_id)
            result = CategoryPublic.model_validate(category)
        return result

    # List

    def list_all(self, offset: int = 0, limit: int = 20) -> CategoryList:
        with CategoryUnitOfWork(self._session) as uow:
            categories = uow.categories.get_all_active(offset, limit)
            total = uow.categories.count_active()

            data = [CategoryPublic.model_validate(c) for c in categories]
            result = CategoryList(data=data, total=total)

        return result

    def list_all_admin(self, offset: int = 0, limit: int = 20) -> CategoryList:
        with CategoryUnitOfWork(self._session) as uow:
            categories = uow.categories.get_all(offset, limit)
            total = uow.categories.count()

            data = [CategoryPublic.model_validate(c) for c in categories]
            result = CategoryList(data=data, total=total)
        return result

    # Update

    def update(self, category_id: int, data: CategoryUpdate) -> CategoryPublic:
        with CategoryUnitOfWork(self._session) as uow:
            category = self._get_active_or_404(uow, category_id)
            list_categories = list(uow.categories.get_all_active_no_paged())
            category_map = self._build_category_map(list_categories)

            if data.parent_id is not None:
                products = uow.category_products.has_products(category_id)
                if products:
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        "No puedes modificar el arbol de jerarquias en una categoria con productos ",
                    )
                if category.id == data.parent_id:
                    raise HTTPException(
                        400, "No puedes asignar la categoria a si misma"
                    )

                self._get_active_or_404(uow, data.parent_id)

                if self._would_create_cycle(category, data.parent_id, category_map):
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST, "Ciclo detectado en jerarquía"
                    )

            if data.name and data.name != category.name:
                self._assert_name_unique(uow, data.name)

            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(category, field, value)

            category.updated_at = datetime.now(timezone.utc)
            uow.categories.add(category)

            result = CategoryPublic.model_validate(category)
        return result

    # Delete (soft)
    # Solo se permite borrar categorias sin productos y sin hijos para evitar inconsistencia de datos
    def delete(self, category_id: int):
        with CategoryUnitOfWork(self._session) as uow:
            category = self._get_active_or_404(uow, category_id)
            children = uow.categories.has_children_active(category_id)
            links = uow.category_products.has_products(category_id)

            if links:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "No se puede eliminar una categoria con productos asociados",
                )
            if children:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "No puedes eliminar una categoria con hijos activos",
                )

            uow.categories.soft_delete(category)

        return status.HTTP_204_NO_CONTENT

    def search_active_by_name(
        self, query: str, offset: int = 0, limit: int = 20
    ) -> CategoryList:
        query = query.strip()
        if not query:
            return CategoryList(data=[], total=0)

        with CategoryUnitOfWork(self._session) as uow:
            categorias = uow.categories.search_active_by_name(query, offset, limit)
            total = uow.categories.count_search_active_by_name(query)

            data = [CategoryPublic.model_validate(c) for c in categorias]
            result = CategoryList(data=data, total=total)

        return result

    def search_all_by_name(
        self, query: str, offset: int = 0, limit: int = 20
    ) -> CategoryList:
        query = query.strip()
        if not query:
            return CategoryList(data=[], total=0)

        with CategoryUnitOfWork(self._session) as uow:
            categorias = uow.categories.search_by_name(query, offset, limit)
            total = uow.categories.count_search_by_name(query)

            data = [CategoryPublic.model_validate(c) for c in categorias]
            result = CategoryList(data=data, total=total)
        return result

    def restore(self, category_id: int) -> CategoryPublic:
        with CategoryUnitOfWork(self._session) as uow:
            category = self._get_or_404(uow, category_id)
            if category.deleted_at is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "La categoria no está eliminada",
                )
            uow.categories.restore(category)
            result = CategoryPublic.model_validate(category)

        return result

    def _build_tree_map(
        self, categories: list[Category]
    ) -> dict[int | None, list[Category]]:
        tree: dict[int | None, list[Category]] = {}

        for c in categories:
            tree.setdefault(c.parent_id, []).append(c)

        return tree

    # Reemplaza _build_tree y _a_nodo por esta versión única
    def _build_tree_recursive(
        self,
        category: Category,
        tree_map: dict[int | None, list[Category]],
        current_depth: int,
        max_depth: int,
        visited: set[int],
    ) -> CategoryTree:

        if category.id in visited:
            raise HTTPException(400, "Ciclo detectado en la base de datos")
        visited.add(category.id)  # type: ignore

        hijos_formateados = []
        if current_depth < max_depth:
            hijos_raw = tree_map.get(category.id, [])
            hijos_formateados = [
                self._build_tree_recursive(
                    hijo, tree_map, current_depth + 1, max_depth, visited.copy()
                )
                for hijo in hijos_raw
                if hijo.deleted_at is None
            ]

        return CategoryTree(
            id=category.id,  # type: ignore
            name=category.name,
            parent_id=category.parent_id,
            children=hijos_formateados,
        )

    def _build_category_map(self, categories: list[Category]) -> dict[int, Category]:
        return {c.id: c for c in categories if c.id is not None}

    def _build_parent_chain(
        self,
        category: Category,
        category_map: dict[int, Category],
    ) -> list[int]:

        result: list[int] = []
        visited: set[int] = set()

        current = category

        while current is not None:
            if current.id in visited:
                raise ValueError("Ciclo detectado en categorias")

            visited.add(current.id)  # type: ignore
            result.append(current.id)  # type: ignore

            if current.parent_id is None:
                break

            current = category_map.get(current.parent_id)

        return result

    def get_full_tree_by_id(self, root_id: int, max_depth: int = 3) -> CategoryTree:
        with CategoryUnitOfWork(self._session) as uow:
            categorias = list(uow.categories.get_all_active_no_paged())
            root = next((c for c in categorias if c.id == root_id), None)

            if not root:
                raise HTTPException(404, "Categoría no encontrada")

            tree_map = self._build_tree_map(categorias)
            return self._build_tree_recursive(root, tree_map, 0, max_depth, set())

    def get_category_chain(self, child_id: int) -> list[int]:
        with CategoryUnitOfWork(self._session) as uow:
            category = self._get_active_or_404(uow, child_id)
            categories_list = list(uow.categories.get_all_active_no_paged())
            category_map = self._build_category_map(categories_list)
            parents_chain_id = self._build_parent_chain(category, category_map)

        return parents_chain_id

    def get_root_categories(self, offset: int = 0, limit: int = 20):
        with CategoryUnitOfWork(self._session) as uow:
            categories = list(uow.categories.get_all_root_active(offset, limit))
            data = [CategoryPublic.model_validate(c) for c in categories]
            count = uow.categories.count_root_active()
            result = CategoryList(data=data, total=count)

        return result

    def _would_create_cycle(self, category, new_parent_id, category_map):

        current = category_map.get(new_parent_id)

        while current:
            if current.id == category.id:
                return True
            current = category_map.get(current.parent_id)

        return False

    def get_full_tree(self, max_depth: int = 3) -> list[CategoryTree]:
        with CategoryUnitOfWork(self._session) as uow:
            categorias = list(uow.categories.get_all_active_no_paged())
            tree_map = self._build_tree_map(categorias)
            raices = [c for c in categorias if c.parent_id is None]

            return [
                self._build_tree_recursive(r, tree_map, 0, max_depth, set())
                for r in raices
            ]
