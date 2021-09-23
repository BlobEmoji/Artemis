import discord


async def get_gallery_embed(bot, link):
    submission = await bot.pool.fetchrow('''
    SELECT * FROM submissions
    WHERE
        image_link = $1
    ''', link)

    if not submission:
        return False

    if not submission['day_num']:
        return False

    try:
        guild = bot.get_guild(bot.c.guild_id)
        submission_channel = guild.get_channel(bot.c.submission_channel_id)
    except:
        return False

    try:
        umsg = await submission_channel.fetch_message(submission['user_post_id'])
    except:
        return False

    e = discord.Embed(title=f'{bot.c.get_prompt(submission["day_num"])} ({submission["day_num"]})', color=bot.c.embed_color, timestamp=umsg.created_at)
    e.set_image(url=submission['image_link'])
    e.set_author(name=umsg.author.name, icon_url=umsg.author.avatar_url)

    return e
