async def get_data(bot):
    info = await bot.pool.fetchval(
        """
        SELECT DISTINCT day_num, user_id FROM submissions
    """,
        bot.owner_id,
    )
