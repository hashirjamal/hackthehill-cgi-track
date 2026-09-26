import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.complaint_routes import router as complaint_router
from app.config import settings
from app.db import Base, engine, get_db
from app.laya_routes import router as laya_router
from app.laya_service import warm_up
from app.models import Item


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Hackathon shortcut: create tables on startup instead of using migrations.
    Base.metadata.create_all(engine)
    if settings.preload_laya:
        # Load the model once at startup, like any ML service, so no request pays for it.
        await asyncio.to_thread(warm_up)
    yield


app = FastAPI(title="Hack the Hill API", lifespan=lifespan)
app.include_router(laya_router)
app.include_router(complaint_router)


class ItemIn(BaseModel):
    name: str


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}


@app.post("/items", response_model=ItemOut)
def create_item(payload: ItemIn, db: Session = Depends(get_db)):
    item = Item(name=payload.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/items", response_model=list[ItemOut])
def list_items(db: Session = Depends(get_db)):
    return db.scalars(select(Item).order_by(Item.id)).all()
