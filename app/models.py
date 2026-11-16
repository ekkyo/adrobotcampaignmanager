from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    keitaro_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(2))
    offers: Mapped[list["CampaignOffer"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
    )


class CampaignOffer(Base):
    __tablename__ = "campaign_offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    offer_id: Mapped[int] = mapped_column(Integer)
    campaign: Mapped[Campaign] = relationship(back_populates="offers")
