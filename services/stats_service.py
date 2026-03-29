from __future__ import annotations

from database import Database


async def get_users_overview(database: Database) -> dict[str, int]:
    return await database.get_user_counts()


async def get_full_stats(database: Database) -> dict[str, int]:
    users = await database.get_user_counts()
    submissions = await database.get_submission_counts()
    return {
        "users_total": users["total"],
        "users_today": users["today"],
        "submissions_total": submissions["total"],
        "submissions_today": submissions["today"],
        "pending": submissions["pending"],
        "published": submissions["published"],
        "rejected": submissions["rejected"],
    }
