import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.beatmap import Beatmap
from app.utils import model_to_dict

if TYPE_CHECKING:
    from app.models.user import User


class Scores(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"))
    beatmap_id: Mapped[int] = mapped_column(ForeignKey("beatmap.beatmap_id"))
    score_ended_at: Mapped[Optional[datetime]] = mapped_column()
    max_combo: Mapped[int] = mapped_column()
    mods: Mapped[Optional[str]] = mapped_column()
    pp: Mapped[Optional[float]] = mapped_column()
    rank: Mapped[str] = mapped_column()
    accuracy: Mapped[Optional[float]] = mapped_column()
    meh: Mapped[Optional[int]] = mapped_column()
    ok: Mapped[Optional[int]] = mapped_column()
    great: Mapped[Optional[int]] = mapped_column()
    miss: Mapped[Optional[int]] = mapped_column()
    passed: Mapped[bool] = mapped_column()
    lazer: Mapped[bool] = mapped_column(default=False)

    user: Mapped["User"] = relationship(back_populates="scores")
    beatmap: Mapped["Beatmap"] = relationship(back_populates="scores")

    @hybrid_property
    def mods_list(self):
        if not self.mods:
            return None
        return self.mods.strip("{}").split(",")

    @classmethod
    async def filter_valid_kwargs(cls, db, score):
        valid_keys = {col.name for col in cls.__table__.columns}

        score_dict = await model_to_dict(score)
        valid_score = dict()

        valid_score["user_id"] = score.user_id
        # remove id from the dictionary, we don't want to populate this field in our db
        logging.debug(f"Score from API for user '{score.user_id}': {score_dict}")
        score_dict.pop("id", None)

        # iterate over statistics and filter out the valid keys
        if score.statistics:
            for s_key, s_value in score_dict.items():
                if s_key in valid_keys:
                    valid_score[s_key] = s_value

            # again iterate over statistics and filter out the valid keys
            if "statistics" in score_dict:
                for stat_key, stat_value in score_dict["statistics"].items():
                    if stat_key in valid_keys:
                        # since we're iterating over the statistics, 300, 100, 50, misses can be None
                        # so just set them to 0
                        valid_score[stat_key] = stat_value if stat_value else 0

        # assign the ended_at field if it exists (must be:D)
        valid_score["score_ended_at"] = getattr(score, "ended_at", None)

        if score.beatmap:
            # Add beatmap to the database if it doesn't exist from the score
            await Beatmap.add(db, score)
            # Add the max_combo to the valid_score from added beatmap
            valid_score["beatmap_id"] = getattr(score.beatmap, "id", None)

            # Remove the beatmap key from the dictionary
            score_dict.pop("beatmap", None)

        mods = score.mods
        # check if there's a "CL" mod, if there is - it's a classic score
        is_lazer_score = not any([mod for mod in mods if mod.acronym == "CL"])
        if is_lazer_score:
            valid_score["lazer"] = True

        if mods:
            valid_score["mods"] = []
            for mod in mods:
                valid_score["mods"].append(mod.acronym)
        else:
            valid_score.pop("mods", None)

        return valid_score

    @classmethod
    async def get(
        cls, db, user_id: int, beatmap_id: int, score_ended_at: Optional[datetime]
    ):
        stmt = select(Scores).where(
            Scores.user_id == user_id,
            Scores.beatmap_id == beatmap_id,
            Scores.score_ended_at == score_ended_at,
        )

        result = await db.scalars(stmt)
        return result.first()

    @classmethod
    async def get_latest(cls, db, user_id: int):
        stmt = (
            select(Scores)
            .where(Scores.user_id == user_id)
            .order_by(Scores.score_ended_at.desc())
        )

        result = await db.scalars(stmt)
        return result.first()

    @classmethod
    async def add(cls, db, score):
        if await cls.get(db, score.user_id, score.beatmap.id, score.ended_at):
            logging.info(f"Score '{score.id}' already exists in the database.")
            return

        valid_score = await cls.filter_valid_kwargs(db, score)
        score = await db.add(cls(**valid_score))
        logging.info(
            f"Score '{score.id}' added for user_id '{score.user_id}', beatmap_id:{score.beatmap_id} at {score.score_ended_at}"
        )
        return score

    @classmethod
    async def delete_all(cls, db, user_id: int):
        stmt = select(Scores).where(Scores.user_id == user_id)
        result = await db.scalars(stmt)
        scores = result.all()
        logging.info(f"Deleting all scores for user '{user_id}'")
        for score in scores:
            await db.delete(score)

    @classmethod
    async def clean_old_scores(cls, db, user_id: int):
        # Subquery to get the last 5 "passed" scores
        passed_sub_stmt = (
            select(Scores.id)
            .where(Scores.user_id == user_id, Scores.passed.is_(True))
            .order_by(Scores.id.desc())
            .limit(5)
        )
        passed_result_sub_stmt = await db.scalars(passed_sub_stmt)

        # Subquery to get the last 5 "not passed" scores
        not_passed_sub_stmt = (
            select(Scores.id)
            .where(Scores.user_id == user_id, Scores.passed.is_(False))
            .order_by(Scores.id.desc())
            .limit(5)
        )
        not_passed_result_sub_stmt = await db.scalars(not_passed_sub_stmt)

        # Combine IDs to exclude the latest "passed" and "not passed" scores
        exclude_ids = set(passed_result_sub_stmt) | set(not_passed_result_sub_stmt)

        # Main query to get all scores except the latest "passed" and "not passed" scores
        stmt = select(Scores).where(
            Scores.user_id == user_id, Scores.id.notin_(exclude_ids)
        )
        result = await db.scalars(stmt)

        # Convert the result to a list and delete old scores
        result_list = result.all()
        for score in result_list:
            await db.delete(score)

        # Log the operation if any scores were deleted
        if result_list:
            logging.info(f"Removed {len(result_list)} old scores for user {user_id}")
