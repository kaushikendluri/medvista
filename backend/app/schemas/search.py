from pydantic import BaseModel


class SearchResultItem(BaseModel):
    type: str  # "patient" | "study" | "report" | "user"
    id: str
    title: str
    subtitle: str | None
    href: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
