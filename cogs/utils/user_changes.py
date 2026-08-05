import logging

from ossapi.models import UserStatistics as OsuApiStatistics

from app.models.user import User as OsuDbUser


async def format_diff_name(api_key: str) -> str:
    """Format API key to a more readable name."""
    if api_key == "pp":
        return "PP"
    if "_" in api_key:
        return " ".join(word.capitalize() for word in api_key.split("_"))

    return api_key.capitalize()


async def calculate_diff(api_value: float, db_value: float) -> str:
    """Calculate the difference and format it as a string."""
    diff = round(api_value - db_value, 2)
    return f"+{diff}" if diff > 0 else str(diff)


async def get_user_changes(
    db_sess, api_user: OsuApiStatistics, user_id: int
) -> list[str]:
    db_user = await OsuDbUser.get(db_sess, user_id)
    if not db_user:
        return []

    api_user_data = api_user._ossapi_data
    ignore_keys = ["play_count", "play_time", "previous_usernames", "hit_accuracy"]

    changes: list[str] = []
    for api_key, api_value in api_user_data.items():
        # Only numbers can be diffed, everything else (strings, None, nested models)
        # would either be meaningless or blow up in calculate_diff
        if not isinstance(api_value, (int, float)) or api_key in ignore_keys:
            continue

        db_value = getattr(db_user, api_key, None)
        if db_value and db_value != api_value:
            logging.info(
                f"Changes for '{user_id}' - '{api_key}' from '{db_value}' to '{api_value}'"
            )
            diff_name = await format_diff_name(api_key)
            diff = await calculate_diff(api_value, db_value)
            arrow = "🔼" if "+" in diff else "🔽"

            if "rank" in api_key.lower():
                arrow = "🔽" if "+" in diff else "🔼"

            changes.append(f"{arrow}`{diff_name}: {diff}`")

    return changes
