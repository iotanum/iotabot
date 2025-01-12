import logging
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import func, select
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.scores import Scores
from app.utils import model_to_dict

if TYPE_CHECKING:
    from app.models.discord_users import DiscordUsers
    from app.models.tracking_channels import TrackingChannels


class User(Base):
    """Represents a user in the database."""

    __tablename__ = "user"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column()
    url: Mapped[str] = mapped_column()
    avatar_url: Mapped[str] = mapped_column()
    country_code: Mapped[str] = mapped_column()
    previous_usernames: Mapped[str] = mapped_column()

    global_rank: Mapped[Optional[int]] = mapped_column()
    country_rank: Mapped[Optional[int]] = mapped_column()
    hit_accuracy: Mapped[float] = mapped_column()
    play_count: Mapped[int] = mapped_column()
    play_time: Mapped[int] = mapped_column()
    pp: Mapped[float] = mapped_column()

    scores: Mapped[Optional[List["Scores"]]] = relationship(back_populates="user")
    tracking_channels: Mapped[Optional[List["TrackingChannels"]]] = relationship(
        back_populates="user"
    )
    discord_users: Mapped[Optional[List["DiscordUsers"]]] = relationship(
        back_populates="user"
    )

    @classmethod
    async def filter_valid_kwargs(cls, user) -> dict:
        """
        Filters valid attributes from a given user object to match the SQLAlchemy model.
        """
        valid_keys = {column.key for column in inspect(cls).attrs}
        model_dict = await model_to_dict(user)
        valid_user = {}

        # Map fields and filter out invalid keys
        if "id" in model_dict:
            valid_user["user_id"] = model_dict["id"]

        for key, value in model_dict.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key in valid_keys:
                        valid_user[sub_key] = sub_value
            elif key in valid_keys:
                valid_user[key] = value

        # Add URL field if user_id is available
        if "user_id" in valid_user:
            valid_user["url"] = f"https://osu.ppy.sh/users/{valid_user['user_id']}"

        return valid_user

    @classmethod
    async def get(cls, db, user: str | int) -> Optional["User"]:
        """
        Retrieves a user by ID or username.
        """
        try:
            user_id = int(user)
            stmt = select(User).where(User.user_id == user_id)
        except ValueError:
            stmt = select(User).where(func.lower(User.username) == func.lower(user))

        result = await db.scalars(stmt)
        return result.first()

    @classmethod
    async def get_all(cls, db) -> List["User"]:
        """
        Retrieves all users from the database.
        """
        return (await db.scalars(select(User))).all()

    @classmethod
    async def add(cls, db, user) -> None:
        """
        Adds a new user to the database if they don't already exist.
        """
        if await cls.get(db, user.id):
            logging.info(
                f"User '{user.username}' with ID '{user.id}' already exists in the database."
            )
            return

        valid_user = await cls.filter_valid_kwargs(user)
        await db.add(User(**valid_user))
        logging.info(
            f"User '{valid_user.get('username')}' added to the database."
        )  # Replace with logging

    @classmethod
    async def remove(cls, db, user_id: int) -> None:
        """
        Removes a user and their associated scores from the database.
        """
        user = await cls.get(db, user_id)
        if not user:
            logging.info(f"User with ID '{user_id}' does not exist in the database.")
            return

        # Remove all associated scores
        stmt = select(Scores).where(Scores.user_id == user_id)
        scores = await db.scalars(stmt)

        for score in scores.all():
            await db.remove(score)
            logging.info(f"Removed score ID '{score.id}' for user '{user.username}'.")

        await db.remove(user)
        logging.info(
            f"User '{user.username}' with ID '{user.user_id}' removed from the database."
        )

    @classmethod
    async def update_from_score(cls, db, score) -> None:
        """
        Updates user attributes based on a score object.
        """
        new_values = {
            "username": score._user.username,
            "avatar_url": score._user.avatar_url,
            "country_code": score._user.country_code,
        }

        user = await cls.get(db, score.user_id)
        if user:
            await db.update(user, new_values)
            logging.info(
                f"Updated user '{user.username}' with new values: {new_values}."
            )

    @classmethod
    async def update_from_stat_change(cls, db, api_user, user_id) -> None:
        """
        Updates user attributes based on the osu! API.
        """

        user = await cls.get(db, user_id)
        if user:
            new_values = await cls.filter_valid_kwargs(api_user)
            new_values.pop("user_id", None)
            await db.update(user, new_values)
            logging.info(
                f"Updated user '{user.username}' with new values: {new_values}."
            )
