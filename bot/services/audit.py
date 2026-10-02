import discord
async def send_log(guild,config,title,description):
    cid=config.get('log_channel_id')
    if not cid:return
    ch=guild.get_channel(cid)
    if ch: await ch.send(embed=discord.Embed(title=title,description=description,color=discord.Color.blurple()))
