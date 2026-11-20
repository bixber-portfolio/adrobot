from pydantic import BaseModel, ConfigDict, Field, field_validator

CAMPAIGN_NAME_MAX_LENGTH = 200
GEO_CODE_LENGTH = 2


class CampaignCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=CAMPAIGN_NAME_MAX_LENGTH)
    geo: str
    offer_id: int = Field(gt=0)

    @field_validator("geo")
    @classmethod
    def geo_is_country_code(cls, value: str) -> str:
        value = value.upper()
        is_code = (
            len(value) == GEO_CODE_LENGTH
            and value.isascii()
            and value.isalpha()
        )
        if not is_code:
            raise ValueError(
                "Гео должно быть двухбуквенным кодом страны, например DE"
            )
        return value


class CampaignRead(BaseModel):
    id: int
    alias: str
    name: str


class CampaignSearchRead(BaseModel):
    id: int
    name: str
    alias: str
    state: str


class OfferRead(BaseModel):
    id: int
    name: str


class StreamOfferRead(BaseModel):
    offer_id: int
    name: str | None
    share: int
    pinned: bool
    removed: bool


class StreamRead(BaseModel):
    id: int
    name: str
    position: int
    stream_schema: str
    editable: bool
    clicks_today: int | None
    dirty: bool
    offers: list[StreamOfferRead]


class CampaignStreamsRead(BaseModel):
    campaign_id: int
    keitaro_url: str
    streams: list[StreamRead]


class StreamEditRead(BaseModel):
    """Состояние одного потока после действия в редакторе."""

    id: int
    dirty: bool
    offers: list[StreamOfferRead]


class AddOfferRequest(BaseModel):
    offer_id: int = Field(gt=0)
