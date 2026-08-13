from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    athlete_name: Mapped[str] = mapped_column(String(255), index=True)
    brand: Mapped[str] = mapped_column(String(120), index=True)
    set_name: Mapped[str] = mapped_column(String(255))
    year: Mapped[int] = mapped_column(index=True)
    card_number: Mapped[str] = mapped_column(String(50), index=True)
    parallel_name: Mapped[str | None] = mapped_column(String(120), default=None)
    grading_company: Mapped[str | None] = mapped_column(String(50), default=None)
    grade: Mapped[str | None] = mapped_column(String(20), default=None)

    sales: Mapped[list["SaleRecord"]] = relationship(back_populates="card", cascade="all, delete-orphan")
