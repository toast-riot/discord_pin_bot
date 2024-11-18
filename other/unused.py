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


# @bot.event
# async def on_message(message: discord.Message):
#     if message.author == bot.user and message.type == discord.MessageType.pins_add:
#         await message.delete()


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