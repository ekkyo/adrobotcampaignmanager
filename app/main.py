import re

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import get_db
from .keitaro import KeitaroClient, KeitaroError
from .models import Campaign, CampaignOffer
from .schemas import CampaignCreate, OfferChange

app = FastAPI(title="Adrobot Campaign Manager")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

OPTIONS = {
    "offers": ("offers", {}),
    "groups": ("groups", {"type": "campaigns"}),
    "domains": ("domains", {}),
    "sources": ("traffic_sources", {}),
}


def equal_shares(offer_ids: list[int]) -> list[dict[str, int]]:
    """Split 100 percent evenly, assigning any remainder to earlier offers."""
    base, remainder = divmod(100, len(offer_ids))
    return [
        {"offer_id": offer_id, "share": base + int(index < remainder)}
        for index, offer_id in enumerate(offer_ids)
    ]


def find_offer_stream(streams: list[dict]) -> dict | None:
    return next(
        (
            stream
            for stream in streams
            if stream.get("schema") == "landings" and not stream.get("filters")
        ),
        None,
    )


def campaign_details(campaign: dict, streams: list[dict]) -> dict:
    offer_stream = find_offer_stream(streams)
    offers = offer_stream.get("offers", []) if offer_stream else []
    countries = [
        country
        for stream in streams
        for filter_ in stream.get("filters", [])
        if filter_.get("name") == "country" and filter_.get("mode") == "accept"
        for country in filter_.get("payload", [])
    ]
    return {
        "id": campaign["id"],
        "keitaro_id": campaign["id"],
        "name": campaign.get("name", ""),
        "country": countries[0] if countries else "—",
        "offers": [
            {"id": offer["offer_id"], "share": offer.get("share", 0)}
            for offer in offers
        ],
        "stream_id": offer_stream.get("id") if offer_stream else None,
    }


async def load_campaign(client: KeitaroClient, campaign_id: int) -> dict:
    campaign = await client.get_campaign(campaign_id)
    streams = await client.streams(campaign_id)
    return campaign_details(campaign, streams)


def api_error(error: KeitaroError) -> HTTPException:
    return HTTPException(status_code=502, detail=str(error))


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/api/campaigns")
async def list_campaigns():
    try:
        result = await KeitaroClient().list("campaigns", limit=500, page=1)
    except KeitaroError as error:
        raise api_error(error) from error

    if isinstance(result, dict):
        result = result.get("campaigns", result.get("data", []))
    return [
        {"id": campaign["id"], "keitaro_id": campaign["id"], "name": campaign.get("name", "")}
        for campaign in result
    ]


@app.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: int):
    try:
        return await load_campaign(KeitaroClient(), campaign_id)
    except KeitaroError as error:
        raise api_error(error) from error


@app.get("/api/options/{kind}")
async def get_options(kind: str):
    if kind not in OPTIONS:
        raise HTTPException(status_code=404, detail="Неизвестный справочник")
    path, params = OPTIONS[kind]
    try:
        return await KeitaroClient().list(path, **params)
    except KeitaroError as error:
        raise api_error(error) from error


@app.post("/api/campaigns", status_code=201)
async def create_campaign(data: CampaignCreate, db: Session = Depends(get_db)):
    country = data.country.upper()
    alias = re.sub(r"[^a-z0-9-]+", "-", data.name.lower()).strip("-") or "campaign"
    client = KeitaroClient()
    campaign_payload = {
        "name": data.name,
        "alias": alias,
        "type": "position",
        "state": "active",
        "domain_id": data.domain_id,
        "group_id": data.group_id,
        "traffic_source_id": data.traffic_source_id,
    }

    try:
        created = await client.create_campaign(campaign_payload)
        campaign_id = created.get("id") if isinstance(created, dict) else None
        if not campaign_id:
            raise KeitaroError("Keitaro не вернул ID созданной кампании")

        await client.create_stream(
            campaign_id,
            {
                "name": "Google",
                "type": "regular",
                "position": 1,
                "state": "active",
                "action_type": "http",
                "action_payload": "https://www.google.com",
                "schema": "redirect",
                "collect_clicks": True,
                "filter_or": False,
                "weight": 0,
                "offer_selection": "before_click",
                "filters": [
                    {"name": "country", "mode": "accept", "payload": [country]}
                ],
                "offers": [],
            },
        )
        await client.create_stream(
            campaign_id,
            {
                "name": "Offers",
                "type": "regular",
                "position": 2,
                "state": "active",
                "action_type": "http",
                "action_payload": "",
                "schema": "landings",
                "collect_clicks": True,
                "filter_or": False,
                "weight": 0,
                "offer_selection": "before_click",
                "filters": [],
                "offers": [
                    {"offer_id": data.offer_id, "share": 100, "state": "active"}
                ],
            },
        )
    except KeitaroError as error:
        raise api_error(error) from error

    local_campaign = Campaign(
        name=data.name,
        country=country,
        keitaro_id=campaign_id,
    )
    local_campaign.offers.append(CampaignOffer(offer_id=data.offer_id))
    db.add(local_campaign)
    db.commit()
    return await load_campaign(client, campaign_id)


@app.post("/api/campaigns/{campaign_id}/offers")
async def add_offer(
    campaign_id: int,
    data: OfferChange,
    db: Session = Depends(get_db),
):
    client = KeitaroClient()
    try:
        current = await load_campaign(client, campaign_id)
        offer_ids = [offer["id"] for offer in current["offers"]]
        if data.offer_id in offer_ids:
            raise HTTPException(status_code=409, detail="Оффер уже добавлен")
        if not current["stream_id"]:
            raise HTTPException(status_code=409, detail="У кампании нет потока офферов")

        updated_offers = equal_shares(offer_ids + [data.offer_id])
        await client.update_stream(current["stream_id"], {"offers": updated_offers})
    except KeitaroError as error:
        raise api_error(error) from error

    local = db.query(Campaign).filter_by(keitaro_id=campaign_id).first()
    if local:
        local.offers.append(CampaignOffer(offer_id=data.offer_id))
        db.commit()

    current["offers"] = [
        {"id": offer["offer_id"], "share": offer["share"]}
        for offer in updated_offers
    ]
    return current


@app.delete("/api/campaigns/{campaign_id}/offers/{offer_id}")
async def remove_offer(
    campaign_id: int,
    offer_id: int,
    db: Session = Depends(get_db),
):
    client = KeitaroClient()
    try:
        current = await load_campaign(client, campaign_id)
        offer_ids = [offer["id"] for offer in current["offers"]]
        if offer_id not in offer_ids:
            raise HTTPException(status_code=404, detail="Оффер не найден в кампании")
        if len(offer_ids) == 1:
            raise HTTPException(status_code=400, detail="Нельзя удалить последний оффер")
        if not current["stream_id"]:
            raise HTTPException(status_code=409, detail="У кампании нет потока офферов")

        updated_offers = equal_shares(
            [item for item in offer_ids if item != offer_id]
        )
        await client.update_stream(current["stream_id"], {"offers": updated_offers})
    except KeitaroError as error:
        raise api_error(error) from error

    local = db.query(Campaign).filter_by(keitaro_id=campaign_id).first()
    if local:
        item = next((offer for offer in local.offers if offer.offer_id == offer_id), None)
        if item:
            local.offers.remove(item)
            db.commit()

    current["offers"] = [
        {"id": offer["offer_id"], "share": offer["share"]}
        for offer in updated_offers
    ]
    return current
