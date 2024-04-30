from auth.api_key_header import api_key_header
from fastapi import APIRouter, Request, Security
from pydantic import BaseModel


class Item(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    tax: float = 10.5
    tags: list[str] = []


items = [
    {"name": "Foo", "price": 50.2},
    {"name": "Bar", "description": "The bartenders", "price": 62, "tax": 20.2},
    {"name": "Baz", "description": None, "price": 50.2, "tax": 10.5, "tags": []},
]

router = APIRouter(tags=["Item"], prefix="/items")


@router.get("")
async def list_items(req: Request, api_key: str = Security(api_key_header)):
    return {"data": items}


@router.post("")
async def create_item(req: Request, item: Item, api_key: str = Security(api_key_header)):
    items.append(item)

    return {"data": item}


@router.get("/{item_id}")
async def get_item(req: Request, item_id: int, api_key: str = Security(api_key_header)):
    return {"data": items[item_id]}


@router.put("/{item_id}")
async def update_item(req: Request, item_id: int, item: Item, api_key: str = Security(api_key_header)):
    items[item_id] = item

    return {"data": item}


@router.delete("/{item_id}")
async def delete_item(req: Request, item_id: int, api_key: str = Security(api_key_header)):
    del items[item_id]

    return {"data": {}}
