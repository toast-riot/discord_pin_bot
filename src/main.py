from os import getenv
from dotenv import load_dotenv
import discord
from discord.ext import commands


def main():
    async def message_pin_or_unpin(interaction: discord.Interaction, message: discord.Message):
        if message.channel.permissions_for(message.guild.me).manage_messages == False:
            await response_followup(interaction, "This bot does not have permission to pin messages here")
            return
        # if (message.author == bot.user and (message.type == discord.MessageType.context_menu_command or message.type == discord.MessageType.chat_input_command) and message.interaction_metadata.user == interaction.user):
        #     await message.delete()
        #     await (await interaction.original_response()).delete()
        #     return
        pinned = message.pinned
        if pinned:
            await message.unpin()
        else:
            try:
                await message.pin()
            except discord.errors.HTTPException as e:
                if e.code == 30003:
                    await response_followup(interaction, "Pin limit reached")
                    return
        await response_followup(interaction, f"Message {'un' if pinned else ''}pinned")

    async def response_followup(interaction: discord.Interaction, content: str):
        await (await interaction.original_response()).edit(content=content)

    async def mod_log(guild: discord.Guild, message: str):
        await guild.text_channels[0].send(message, allowed_mentions = discord.AllowedMentions(users=False))

    async def build_log(initiator: discord.User, target: discord.User, action: str, reason: str = None, extra: str = None):
        reason = f" with reason `{reason}`" if reason else ""
        extra = f" {extra}" if extra else ""
        return f"{initiator.mention} (`{initiator.name}`) {action} {target.mention} (`{target.name}`){extra}{reason}"

    #- Setup
    load_dotenv(".env")

    intents = discord.Intents.default()
    intents.moderation = True
    intents.message_content = True

    bot = commands.Bot(command_prefix="", intents=intents)


    #- Main
    @bot.event
    async def on_ready():
        print(f"Connected => {bot.user}")

    @bot.event
    async def on_message(message: discord.Message):
        # await bot.tree.sync()
        # print(f"{message.author}: {message.content}")
        if message.author == bot.user and message.type == discord.MessageType.pins_add:
            await message.delete()


    @bot.event
    async def on_audit_log_entry_create(entry: discord.AuditLogEntry):
        reason = entry.reason if entry.reason else None
        initiator = await bot.fetch_user(entry.user_id)
        if entry.action == discord.AuditLogAction.member_update and entry.changes.after.timed_out_until:
            target = await bot.fetch_user(entry.target.id)
            until = int(entry.changes.after.timed_out_until.timestamp())
            message = await build_log(initiator, target, "timed out", reason, f"until <t:{until}:f>")
            await mod_log(entry.guild, message)
        elif entry.action == discord.AuditLogAction.ban:
            target = await bot.fetch_user(entry.target.id)
            message = await build_log(initiator, target, "banned", reason)
            await mod_log(entry.guild, message)
        elif entry.action == discord.AuditLogAction.kick:
            target = await bot.fetch_user(entry.target.id)
            message = await build_log(initiator, target, "kicked", reason)
            await mod_log(entry.guild, message)


    @bot.tree.command(
        name="test"
    )
    async def test(interaction: discord.Interaction, user: discord.User=None, channel: discord.TextChannel=None):
        await interaction.response.send_message(f"{user.name} {user.global_name} {user.display_name} {user.mention} {user.id}")


    @bot.tree.context_menu(
        name="Pin / Unpin Message"
    )
    async def pin_message_context(interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer()
        await message_pin_or_unpin(interaction, message)


    @bot.tree.command(
        name="count_pins",
        description="Get the number of pinned messages in a channel",
    )
    async def count_pins(interaction: discord.Interaction, channel: discord.TextChannel = None):
        await interaction.response.defer()
        if channel is None:
            channel = interaction.channel
        try:
            pins = await channel.pins()
        except discord.errors.Forbidden:
            await response_followup(interaction, f"This bot does not have permission to access <#{channel.id}>")
            return
        await response_followup(interaction, f"<#{channel.id}> has {len(pins)}/50 pinned messages")


    #- Start
    bot.run(getenv("TOKEN"))

if __name__ == "__main__":
    main()
