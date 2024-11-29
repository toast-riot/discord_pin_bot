from os import getenv
from dotenv import load_dotenv
import discord
from discord.ext import commands
from urllib.parse import urlparse


def main():
    async def channel_by_name(guild: discord.Guild, name: str):
        return discord.utils.get(guild.text_channels, name=name)


    async def get_embed(message: discord.Message):
        embed = discord.Embed(
            description = message.content,
            color = 0x2b2d31,
            url=message.jump_url # Used to quickly find duplicate pins
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

        return embed


    async def mod_log(guild: discord.Guild, message: str):
        mod_log_channel = await channel_by_name(guild, CONFIG["mod_log_channel"])
        if not mod_log_channel:
            print(f"WARNING: Mod log channel not found (looking for #{CONFIG['mod_log_channel']})")
            return
        if not mod_log_channel.permissions_for(guild.me).view_channel:
            print(f"WARNING: Missing permissions to view #{CONFIG['mod_log_channel']}")
            return
        if not mod_log_channel.permissions_for(guild.me).send_messages:
            print(f"WARNING: Missing permissions to send messages in #{CONFIG['mod_log_channel']}")
            return
        await mod_log_channel.send(message, allowed_mentions = discord.AllowedMentions(users=False))


    async def build_log(initiator: discord.User, action: str, target: discord.User, reason: str = None, extra: str = None):
        reason = f" with reason `{reason}`" if reason else ""
        extra = f" {extra}" if extra else ""
        return f"{initiator.mention} (`{initiator.name}`) {action} {target.mention} (`{target.name}`){extra}{reason}"


    async def perm_error(interaction: discord.Interaction, message: str):
        await interaction.edit_original_response(content=f"{CONFIG["permission_error_message"]} {message}")


    async def pinboard(interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer()

        should_be_nsfw = message.channel.is_nsfw()
        if should_be_nsfw:
            channel_to_get = CONFIG["nsfw_pins_channel"]
        else:
            channel_to_get = CONFIG["pins_channel"]

        pin_channel = await channel_by_name(message.guild, channel_to_get)

        if not pin_channel:
            await interaction.edit_original_response(content=f"Pinboard channel not found (looking for `#{channel_to_get}`)")
            return
        if not pin_channel.permissions_for(message.guild.me).view_channel:
            await perm_error(interaction, f"view {pin_channel.mention}")
            return
        if not pin_channel.permissions_for(message.guild.me).send_messages:
            await perm_error(interaction, f"send messages in {pin_channel.mention}")
            return
        if not pin_channel.permissions_for(message.guild.me).embed_links:
            await perm_error(interaction, f"embed links in {pin_channel.mention}")
            return
        if should_be_nsfw and not pin_channel.is_nsfw():
            await interaction.edit_original_response(content=f"{pin_channel.mention} must be marked as NSFW")
            return

        # Check if message is already pinned
        if CONFIG["duplicate_pins_check_count"] > 0:
            if not pin_channel.permissions_for(message.guild.me).read_message_history:
                await perm_error(interaction, f"read message history in {pin_channel.mention}")
                return

            async for pin_message in pin_channel.history(limit=CONFIG["duplicate_pins_check_count"]):
                current = pin_message.embeds and pin_message.embeds[0] and pin_message.embeds[0].url or None
                if current == message.jump_url:
                    await interaction.edit_original_response(content=f"Message is already pinned at {pin_message.jump_url}")
                    return

        embed = await get_embed(message)
        await pin_channel.send(embed=embed)

        await interaction.edit_original_response(content=f"Message pinned to {pin_channel.mention}")


    #- Setup
    load_dotenv(".env")

    CONFIG = {
        "mod_log_channel": getenv("MOD_LOG_CHANNEL"),
        "pins_channel": getenv("PINS_CHANNEL"),
        "nsfw_pins_channel": getenv("NSFW_PINS_CHANNEL"),
        "permission_error_message": getenv("PERMISSION_ERROR_MESSAGE"),
        "duplicate_pins_check_count": int(getenv("DUPLICATE_PINS_CHECK_COUNT"))
    }

    intents = discord.Intents.default()
    intents.moderation = True
    intents.message_content = True # Mostly just for consistency

    bot = commands.Bot(command_prefix="", intents=intents)



    #- Main
    @bot.event
    async def on_ready():
        print(f"Connected => {bot.user}")

        for guild in bot.guilds:
            if not guild.me.guild_permissions.view_audit_log:
                print(f"WARNING: Missing permissions to view audit log in {guild.name}")


    @bot.event
    async def on_message(message: discord.Message): # This intentionally prevents the bot checking for plaintext commands
        pass


    @bot.event
    async def on_audit_log_entry_create(entry: discord.AuditLogEntry):
        message = {
            "initiator": None,
            "action": None,
            "target": None,
            "reason": entry.reason or None,
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
        name="sync"
    )
    async def sync(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.id == interaction.guild.owner_id:
            await interaction.edit_original_response(content="You must be an administrator to use this command")
            return
        await bot.tree.sync()
        await interaction.edit_original_response(content="Commands synced")


    @bot.tree.context_menu(
        name="Pin Message"
    )
    async def channel_pin_message_context(interaction: discord.Interaction, message: discord.Message):
        await pinboard(interaction, message)


    # @bot.tree.context_menu(
    #     name="Unpin Message"
    # )
    # async def channel_unpin_message_context(interaction: discord.Interaction, message: discord.Message):
    #     await interaction.response.defer(ephemeral=True)
    #     if message.author == bot.user:
    #         fields = message.embeds and message.embeds[0] and message.embeds[0].fields or None
    #         if fields:
    #             user = discord.utils.get(fields, name="User")
    #             if user and user.value:
    #                 if interaction.user.mention in user.value:
    #                     await message.delete()
    #                     await interaction.edit_original_response(content="Pin removed")
    #                     return
    #             await interaction.edit_original_response(content="You are not the author of this pinned message")
    #             return
    #     await interaction.edit_original_response(content="Message is not recognized as a pinned message")
    #     return


    #- Start
    bot.run(getenv("TOKEN"))

if __name__ == "__main__":
    main()