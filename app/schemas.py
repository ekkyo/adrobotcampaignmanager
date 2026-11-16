from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    country: str = Field(min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")
    offer_id: int = Field(gt=0)
    domain_id: int = Field(gt=0)
    group_id: int = Field(gt=0)
    traffic_source_id: int = Field(gt=0)


class OfferChange(BaseModel):
    offer_id: int = Field(gt=0)
