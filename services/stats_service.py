from __future__ import annotations


async def get_users_overview(database) -> dict:
    return await database.get_user_counts()


async def get_full_stats(database) -> dict:
    users = await database.get_user_counts()
    submissions = await database.get_submission_counts()
    giveaway = await database.get_giveaway_stats()
    return {
        "users": users,
        "submissions": submissions,
        "giveaway": giveaway,
    }
