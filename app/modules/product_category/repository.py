from sqlmodel import Session, select, delete
from typing import Sequence
from app.modules.product_category.models import ProductCategoryLink


class ProductCategoryLinkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # metodos para agregar un link o una lista de links
    def add(self, link: ProductCategoryLink) -> None:
        self.session.add(link)

    def add_many(self, links: list[ProductCategoryLink]) -> None:
        self.session.add_all(links)

    # Busca lista de categorias por producto
    def get_by_product_id(self, product_id: int) -> Sequence[ProductCategoryLink]:
        statement = (
            select(ProductCategoryLink)
            .where(ProductCategoryLink.product_id == product_id)
            .options(select)
        )
        return self.session.exec(statement).all()

    # Busca categoria primaria por producto
    def get_primary_by_product_id(self, product_id: int) -> ProductCategoryLink | None:
        statement = select(ProductCategoryLink).where(
            ProductCategoryLink.product_id == product_id,
            ProductCategoryLink.is_primary == True,
        )
        return self.session.exec(statement).first()

    # borrado fisico de link
    def delete_by_product_id(self, product_id: int) -> None:
        statement = delete(ProductCategoryLink).where(
            ProductCategoryLink.product_id == product_id
        )
        self.session.exec(statement)

    # busca solo por categoria
    def get_by_category_id(self, category_id: int) -> Sequence[ProductCategoryLink]:
        statement = select(ProductCategoryLink).where(
            ProductCategoryLink.category_id == category_id
        )
        return self.session.exec(statement).all()

    # busca por categoria y producto
    def exists_by_product_and_category(self, product_id: int, category_id: int) -> bool:
        statement = select(ProductCategoryLink).where(
            ProductCategoryLink.product_id == product_id,
            ProductCategoryLink.category_id == category_id,
        )
        return self.session.exec(statement).first() is not None

    # Crea automaticamente la cadena de categoria producto enviando solo una lista de id de categoria
    # se coloca correctamente is_primary al compararla con la primary id marcada por el usuario
    def create_chain(
        self,
        product_id: int,
        category_ids: list[int],
        primary_id: int,
    ) -> None:
        links = [
            ProductCategoryLink(
                product_id=product_id,
                category_id=cid,
                is_primary=(cid == primary_id),
            )
            for cid in category_ids
        ]

        self.session.add_all(links)

    def has_products(self, category_id: int) -> bool:
        statement = select(ProductCategoryLink).where(
            ProductCategoryLink.category_id == category_id
        )

        return self.session.exec(statement).first() is not None
