from os import getenv
from dotenv import load_dotenv
import discord
from discord.ext import commands
from urllib.parse import urlparse


def main():
    async def channel_by_name(guild: discord.Guild, name: str):
        return discord.utils.get(guild.text_channels, name=name)


    async def get_embed(message: discord.Message):
        main_embed = discord.Embed(
            description = message.content,
            color = 0x2b2d31,
            # timestamp = message.created_at
        )
        # main_embed.add_field(name="", value="", inline=False) # Spacer

        if message.embeds:
            data = message.embeds[0]
            if data.type == "image":
                main_embed.set_image(url=data.url)

        if message.attachments:
            attachment = message.attachments[0]
            path = urlparse(attachment.url).path
            if path.lower().endswith(("png", "jpeg", "jpg", "gif", "webp")):
                main_embed.set_image(url=attachment.url)
            else:
                main_embed.add_field(name="Attachment", value=f"-# {attachment.url}", inline=False)

        secondary_embed = discord.Embed(
            color = 0x2b2d31
        )
        secondary_embed.add_field(name="User", value=f"-# {message.author.mention}")
        secondary_embed.add_field(name="Link", value=f"-# {message.jump_url}")

        main_embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        # embed.set_footer(text=f"#{message.channel.name}")

        return secondary_embed


    async def webhook_send(channel: discord.TextChannel, username: str, avatar_url: str, content, embed=None):
        webhooks = await channel.webhooks()
        webhook = discord.utils.get(webhooks, name='temp')

        if not webhook:
            webhook = await channel.create_webhook(name='temp', avatar=None)

        await webhook.send(content=content, username=username, avatar_url=avatar_url, embed=embed)
        await webhook.delete()


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

        await webhook_send(pin_channel, message.author.display_name, message.author.display_avatar.url, message.content, embed)
        # pin_message = await pin_channel.send(embeds=embeds, allowed_mentions=discord.AllowedMentions.none())
        await response_followup(interaction, f"Message pinned to {pin_channel.mention}")


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
    async def on_message(message: discord.Message): # This intentionally prevents the bot checking for plaintext commands
        pass
        # await bot.tree.sync()
        # print(f"{message.author}: {message.content}")


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
        # await interaction.response.send_message(f"{user.name} {user.global_name} {user.display_name} {user.mention} {user.id}")
        await webhook_send(channel, user.name, user.display_avatar.url, "Test")
        await interaction.response.send_message("Done")


    @bot.tree.context_menu(
        name="Pin Message"
    )
    async def channel_pin_message_context(interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer()
        await pinboard(interaction, message)


    #- Start
    bot.run(getenv("TOKEN"))

if __name__ == "__main__":
    main()
