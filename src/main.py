from os import getenv
from dotenv import load_dotenv
import discord
from discord.ext import commands
from urllib.parse import urlparse


def main():
    async def channel_by_name(guild: discord.Guild, name: str):
        return discord.utils.get(guild.text_channels, name=name)

    # async def message_pin_or_unpin(interaction: discord.Interaction, message: discord.Message):
    #     if message.channel.permissions_for(message.guild.me).manage_messages == False:
    #         await response_followup(interaction, "This bot does not have permission to pin messages here")
    #         return
    #     pinned = message.pinned
    #     if pinned:
    #         await message.unpin()
    #     else:
    #         try:
    #             await message.pin()
    #         except discord.errors.HTTPException as e:
    #             if e.code == 30003:
    #                 await response_followup(interaction, "Pin limit reached")
    #                 return
    #     await response_followup(interaction, f"Message {'un' if pinned else ''}pinned")


    async def get_embed(message: discord.Message):
        embed = discord.Embed(
            description = message.content,
            color = 0x2b2d31,
            # timestamp = message.created_at
        )
        embed.add_field(name="", value="", inline=False) # Spacer

        if message.embeds:
            data = message.embeds[0]
            if data.type == "image":
                embed.set_image(url=data.url)

        if message.attachments:
            attachment = message.attachments[0]
            path = urlparse(attachment.url).path
            if path.lower().endswith(("png", "jpeg", "jpg", "gif", "webp")):
                embed.set_image(url=attachment.url)
            else:
                embed.add_field(name="Attachment", value=f"-# {attachment.url}", inline=False)

        embed.add_field(name="User", value=f"-# {message.author.mention}")
        embed.add_field(name="Link", value=f"-# {message.jump_url}")

        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        # embed.set_footer(text=f"#{message.channel.name}")

        return embed


    async def response_followup(interaction: discord.Interaction, content: str):
        await (await interaction.original_response()).edit(content=content)


    async def mod_log(guild: discord.Guild, message: str):
        mod_log_channel = await channel_by_name(guild, CONFIG["mod_log_channel"])
        await mod_log_channel.send(message, allowed_mentions = discord.AllowedMentions(users=False))


    async def build_log(initiator: discord.User, action: str, target: discord.User, reason: str = None, extra: str = None):
        reason = f" with reason `{reason}`" if reason else ""
        extra = f" {extra}" if extra else ""
        return f"{initiator.mention} (`{initiator.name}`) {action} {target.mention} (`{target.name}`){extra}{reason}"


    async def pinboard(interaction: discord.Interaction, message: discord.Message):
        embed = await get_embed(message)

        if message.channel.is_nsfw():
            pin_channel = await channel_by_name(message.guild, CONFIG["nsfw_pins_channel"])
        else:
            pin_channel = await channel_by_name(message.guild, CONFIG["pins_channel"])
        pin_message = await pin_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        await response_followup(interaction, f"Message pinned to <#{pin_message.channel.id}>")


    #- Setup
    load_dotenv(".env")

    CONFIG = {
        "mod_log_channel": getenv("MOD_LOG_CHANNEL"),
        "pins_channel": getenv("PINS_CHANNEL"),
        "nsfw_pins_channel": getenv("NSFW_PINS_CHANNEL")
    }

    intents = discord.Intents.default()
    intents.moderation = True
    intents.message_content = True

    bot = commands.Bot(command_prefix="", intents=intents)



    #- Main
    @bot.event
    async def on_ready():
        print(f"Connected => {bot.user}")


    @bot.event
    async def on_message(message: discord.Message): # This stops the bot checking for commands
        pass
        # await bot.tree.sync()
        # print(f"{message.author}: {message.content}")
        # if message.author == bot.user and message.type == discord.MessageType.pins_add:
        #     await message.delete()


    @bot.event
    async def on_audit_log_entry_create(entry: discord.AuditLogEntry):
        message = {
            "initiator": None,
            "action": None,
            "target": None,
            "reason": entry.reason if entry.reason else None,
            "extra": None
        }

        if entry.action == discord.AuditLogAction.member_update and entry.changes.after.timed_out_until:
            until = int(entry.changes.after.timed_out_until.timestamp())
            message["extra"] = f"until <t:{until}:f>"
            message["action"] = "timed out"
        elif entry.action == discord.AuditLogAction.ban:
            message["action"] = "banned"
        elif entry.action == discord.AuditLogAction.kick:
            message["action"] = "kicked"
        else:
            return

        message["initiator"] = await bot.fetch_user(entry.user_id)
        message["target"] = await bot.fetch_user(entry.target.id)
        message = await build_log(**message)
        await mod_log(entry.guild, message)


    @bot.tree.command(
        name="test"
    )
    async def test(interaction: discord.Interaction, user: discord.User=None, channel: discord.TextChannel=None):
        await interaction.response.send_message(f"{user.name} {user.global_name} {user.display_name} {user.mention} {user.id}")


    @bot.tree.context_menu(
        name="Pin Message"
    )
    async def channel_pin_message_context(interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer()
        await pinboard(interaction, message)


    # @bot.tree.command(
    #     name="count_pins",
    #     description="Get the number of pinned messages in a channel",
    # )
    # async def count_pins(interaction: discord.Interaction, channel: discord.TextChannel = None):
    #     await interaction.response.defer()
    #     if channel is None:
    #         channel = interaction.channel
    #     try:
    #         pins = await channel.pins()
    #     except discord.errors.Forbidden:
    #         await response_followup(interaction, f"This bot does not have permission to access <#{channel.id}>")
    #         return
    #     await response_followup(interaction, f"<#{channel.id}> has {len(pins)}/50 pinned messages")


    # @bot.tree.context_menu(
    #     name="Pin / Unpin Message"
    # )
    # async def pin_message_context(interaction: discord.Interaction, message: discord.Message):
    #     await interaction.response.defer()
    #     await message_pin_or_unpin(interaction, message)


    #- Start
    bot.run(getenv("TOKEN"))

if __name__ == "__main__":
    main()
