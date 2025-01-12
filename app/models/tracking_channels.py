import logging
from typing import TYPE_CHECKING, Sequence

import discord
from sqlalchemy import ForeignKey, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.scores import Scores

if TYPE_CHECKING:
    from app.models.user import User


class TrackingChannels(Base):
    """Represents channels being tracked for a user."""

    __tablename__ = "tracking_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"))
    channel_id: Mapped[int] = mapped_column()
    channel_name: Mapped[str] = mapped_column()
    guild_id: Mapped[int] = mapped_column()
    guild_name: Mapped[str] = mapped_column()

    user: Mapped["User"] = relationship(back_populates="tracking_channels")

    @classmethod
    async def get(
        cls, db_session: AsyncSession, user_id: int, interaction: discord.Interaction
    ) -> list["TrackingChannels"]:
        """Fetches tracking channels for a given user and interaction channel."""
        stmt = select(cls).where(
            cls.user_id == user_id, cls.channel_id == interaction.channel_id
        )
        result = await db_session.scalars(stmt)
        return result.all()

    @classmethod
    async def get_by_channel(
        cls, db_session: AsyncSession, interaction: discord.Interaction
    ) -> Sequence["TrackingChannels"]:
        """Fetches tracking channels for a given channel."""
        stmt = select(cls).where(cls.channel_id == interaction.channel_id)
        result = await db_session.scalars(stmt)
        return result.all()

    @classmethod
    async def add(
        cls, db_session: AsyncSession, user_id: int, interaction: discord.Interaction
    ) -> None:
        """Adds a tracking channel for the user if it does not already exist."""
        if await cls.get(db_session, user_id, interaction):
            return

        tracking_channel = TrackingChannels(
            user_id=user_id,
            channel_id=interaction.channel_id,
            channel_name=interaction.channel.name,
            guild_id=interaction.guild_id,
            guild_name=interaction.guild.name,
        )
        await db_session.add(tracking_channel)
        logging.info(
            f"Added '{user_id}' to tracking in '{interaction.channel.name}' in '{interaction.guild.name}'"
        )

    @classmethod
    async def delete(
        cls, db_session: AsyncSession, user_id: int, interaction: discord.Interaction
    ) -> None:
        """Deletes a tracking channel for the user and cleans up related scores."""
        tracked_channels = await cls.get(db_session, user_id, interaction)
        if not tracked_channels:
            return

        tracking_channel = tracked_channels[0]
        await db_session.delete(tracking_channel)

        logging.info(
            f"Deleted '{user_id}' from tracking in '{interaction.channel.name}' in '{interaction.guild.name}'"
        )

        # Clean up related scores
        await Scores.delete_all(db_session, user_id)

    @classmethod
    async def get_all(cls, db_session: AsyncSession) -> Sequence["TrackingChannels"]:
        """Fetches all tracking channels."""
        stmt = select(cls)
        result = await db_session.scalars(stmt)
        return result.all()
