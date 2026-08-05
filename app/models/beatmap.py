import logging
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, inspect, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.beatmapset import Beatmapset
from app.utils import model_to_dict

if TYPE_CHECKING:
    from app.models.beatmapset import Beatmapset
    from app.models.scores import Scores


class Beatmap(Base):
    """Represents a beatmap in the database."""

    __tablename__ = "beatmap"

    beatmap_id: Mapped[int] = mapped_column(primary_key=True)
    beatmapset_id: Mapped[int] = mapped_column(ForeignKey("beatmapset.beatmapset_id"))
    beatmapset: Mapped["Beatmapset"] = relationship(back_populates="beatmaps")
    scores: Mapped[List["Scores"]] = relationship(back_populates="beatmap")

    version: Mapped[str] = mapped_column()
    bpm: Mapped[Optional[float]] = mapped_column()
    max_combo: Mapped[Optional[int]] = mapped_column()
    difficulty_rating: Mapped[float] = mapped_column()
    total_length: Mapped[int] = mapped_column()
    ar: Mapped[float] = mapped_column()
    cs: Mapped[float] = mapped_column()
    drain: Mapped[float] = mapped_column()
    accuracy: Mapped[float] = mapped_column()
    cover_url: Mapped[str] = mapped_column()
    status: Mapped[Optional[str]] = mapped_column()
    url: Mapped[str] = mapped_column()

    @classmethod
    async def filter_valid_kwargs(cls, score) -> dict:
        """
        Filters and maps valid attributes from a Score instance to the Beatmap model.
        """
        valid_keys = {column.key for column in inspect(cls).attrs}

        # Extract and validate beatmap data from the score
        beatmap_data = getattr(score, "beatmap", None)
        if not beatmap_data:
            raise ValueError(
                "The provided Score instance does not contain a valid 'beatmap' attribute."
            )
        beatmap_dict = await model_to_dict(beatmap_data)

        # `None` is never collected, so an update can only ever replace a stored
        # value with a real one
        valid_beatmap = {}
        for key, value in beatmap_dict.items():
            if value is None:
                continue
            if key == "id":  # Map external `id` to `beatmap_id`
                valid_beatmap["beatmap_id"] = value
            elif key in {"beatmapset_id"} or key in valid_keys:
                valid_beatmap[key] = value

        # Remove unwanted keys and add additional fields
        valid_beatmap.pop("beatmapset", None)  # Remove `beatmapset` if present
        # The full-width banner, not the small `list` thumbnail - the score post
        # renders it as a hero image across the top of the card
        cover_url = getattr(score.beatmapset.covers, "cover_2x", None)
        if cover_url:
            valid_beatmap["cover_url"] = cover_url

        return valid_beatmap

    @classmethod
    async def get(cls, db, beatmap_id: int) -> "Beatmap | None":
        """
        Retrieves a beatmap by its ID.
        """
        stmt = select(cls).where(cls.beatmap_id == beatmap_id)
        result = await db.scalars(stmt)
        return result.first()

    @classmethod
    async def add(cls, db, score) -> "Beatmap | None":
        """
        Adds a new beatmap to the database if it doesn't already exist.
        """
        existing_beatmap = await cls.get(db, score.beatmap.id)
        if existing_beatmap:
            logging.info(
                f"Beatmap '{score.beatmap.version}' with ID '{score.beatmap.id}' already exists in the database."
            )
            await cls.update(db, score)
            return None

        # Prepare beatmapset and add it first
        await Beatmapset.add(db, score.beatmapset)

        # Filter valid attributes and create a new Beatmap entry
        valid_beatmap = await cls.filter_valid_kwargs(score)
        new_beatmap = cls(**valid_beatmap)
        await db.add(new_beatmap)
        logging.info(
            f"Added Beatmap '{valid_beatmap.get('version')}' with ID '{valid_beatmap.get('beatmap_id')}' to the database."
        )
        return new_beatmap

    @classmethod
    async def update(cls, db, score) -> None:
        """
        Updates an existing beatmap entry in the database.

        Maps get reworked and re-ranked, so every field is refreshed and not just
        the status - otherwise values like bpm or difficulty stay at whatever
        they were when the beatmap was first cached.
        """

        beatmap = await cls.get(db, score.beatmap.id)
        if beatmap:
            new_values = await cls.filter_valid_kwargs(score)
            # Never rewrite the identity: a beatmap doesn't move to another set,
            # and the beatmapset row is only guaranteed to exist on the add path
            new_values.pop("beatmap_id", None)
            new_values.pop("beatmapset_id", None)
            await db.update(beatmap, new_values)
            logging.info(
                f"Updated beatmap '{score.beatmap.id}' with new values: {new_values}."
            )
