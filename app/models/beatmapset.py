import logging
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import inspect, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.utils import model_to_dict

if TYPE_CHECKING:
    from app.models.beatmap import Beatmap


class Beatmapset(Base):
    """Represents a beatmapset in the database."""

    __tablename__ = "beatmapset"

    beatmapset_id: Mapped[int] = mapped_column(primary_key=True)
    beatmaps: Mapped[List["Beatmap"]] = relationship(back_populates="beatmapset")
    artist: Mapped[Optional[str]] = mapped_column()
    artist_unicode: Mapped[str] = mapped_column()
    title: Mapped[Optional[str]] = mapped_column()
    title_unicode: Mapped[str] = mapped_column()
    creator: Mapped[str] = mapped_column()

    @classmethod
    async def filter_valid_kwargs(cls, beatmapset) -> dict:
        """
        Filters and maps valid attributes from a given beatmapset object.
        """
        valid_keys = {column.key for column in inspect(cls).attrs}
        beatmapset_dict = await model_to_dict(beatmapset)
        valid_beatmapset = {}

        # Map and filter valid keys
        for key, value in beatmapset_dict.items():
            if key == "id":  # Map external `id` to `beatmapset_id`
                valid_beatmapset["beatmapset_id"] = value
            elif key in valid_keys:
                valid_beatmapset[key] = value

        # Remove any unwanted keys explicitly
        valid_beatmapset.pop("beatmaps", None)

        return valid_beatmapset

    @classmethod
    async def get(cls, db, beatmapset_id: int) -> "Beatmapset | None":
        """
        Retrieves a beatmapset by its ID.
        """
        stmt = select(cls).where(cls.beatmapset_id == beatmapset_id)
        result = await db.scalars(stmt)
        return result.first()

    @classmethod
    async def add(cls, db, beatmapset) -> None:
        """
        Adds a new beatmapset to the database if it doesn't already exist.
        """
        existing_beatmapset = await cls.get(db, beatmapset.id)
        if existing_beatmapset:
            logging.info(
                f"Beatmapset '{existing_beatmapset.title_unicode}' "
                f"with ID '{existing_beatmapset.beatmapset_id}' already exists in the database."
            )
            return

        valid_beatmapset = await cls.filter_valid_kwargs(beatmapset)
        await db.add(cls(**valid_beatmapset))
        logging.info(
            f"Beatmapset '{valid_beatmapset.get('title_unicode')}' added to the database."
        )
