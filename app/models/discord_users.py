import logging
from typing import Optional

import discord
from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.user import User


class DiscordUsers(Base):
    """Represents a user in the database."""

    __tablename__ = "discord_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"))
    discord_user_id: Mapped[int] = mapped_column()

    user: Mapped["User"] = relationship(back_populates="discord_users")

    @classmethod
    async def add(
        cls, db, osu_user: User, interaction: discord.Interaction
    ) -> Optional["DiscordUsers"]:
        """
        Add a Discord user to the database.
        """
        exists = await cls.get(db, interaction)
        if exists:
            return

        discord_user = cls(
            discord_user_id=interaction.user.id, user_id=osu_user.user_id
        )
        discord_user = await db.add(discord_user)
        return discord_user

    @classmethod
    async def get(
        cls, db, interaction: discord.Interaction
    ) -> Optional["DiscordUsers"]:
        """
        Get a Discord user by their ID.
        """
        stmt = select(cls).where(cls.discord_user_id == interaction.user.id)
        result = await db.scalars(stmt)
        return result.first()

    @classmethod
    async def update(cls, db, osu_user: User, interaction: discord.Interaction) -> None:
        """
        Updates user attributes based on a score object.
        """
        new_values = {
            "user_id": osu_user.user_id,
            "discord_user_id": interaction.user.id,
        }

        discord_user = await cls.get(db, interaction)
        if discord_user:
            await db.update(discord_user, new_values)
            logging.info(
                f"Updated DiscordUser '{interaction.user.name}' with new values: {osu_user.user_id}."
            )
