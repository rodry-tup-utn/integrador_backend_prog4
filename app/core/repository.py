from typing import Generic, TypeVar, Type, Sequence
from sqlmodel import Session, SQLModel, select
from sqlalchemy import func

ModelT = TypeVar("ModelT", bound=SQLModel)


class BaseRepository(Generic[ModelT]):

    def __init__(self, session: Session, model: Type[ModelT]) -> None:

        self.session = session
        self.model = model

    def get_by_id(self, record_id: int) -> ModelT | None:

        return self.session.get(self.model, record_id)

    def get_all(self, offset: int = 0, limit: int = 20) -> Sequence[ModelT]:

        return self.session.exec(select(self.model).offset(offset).limit(limit)).all()

    def count(self) -> int:
        statement = select(func.count()).select_from(self.model)
        return self.session.exec(statement).one()

    def add(self, instance: ModelT) -> ModelT:

        self.session.add(instance)
        self.session.flush()  # obtiene el ID sin hacer commit
        self.session.refresh(instance)
        return instance

    def delete(self, instance: ModelT) -> None:

        self.session.delete(instance)
        self.session.flush()
