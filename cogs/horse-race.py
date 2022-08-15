# horse-race.py

import re

import discord
from discord.ext import commands

from database import errors, reminders, users
from resources import emojis, exceptions, functions, settings, strings


class HorseRaceCog(commands.Cog):
    """Cog that contains the horse race detection"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""
        if message.author.id != settings.EPIC_RPG_ID: return
        if message.embeds: return
        message_content = message.content
        search_strings = [
            'the next race is in', #English
            'la siguiente carrera es en', #Spanish
            'próxima corrida é em', #Portuguese
        ]
        if any(search_string in message_content.lower() for search_string in search_strings):
            user_name = None
            user = await functions.get_interaction_user(message)
            slash_command = True
            if user is None:
                slash_command = False
                if message.mentions:
                    user = message.mentions[0]
                else:
                    user_name_match = re.search(r"^\*\*(.+?)\*\*,", message_content)
                    if user_name_match:
                        user_name = await functions.encode_text(user_name_match.group(1))
                    else:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in horse race message.', message)
                        return
                    user = await functions.get_guild_member_by_name(message.guild, user_name)
            if user is None:
                await functions.add_warning_reaction(message)
                await errors.log_error('User not found in horse race message.', message)
                return
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return
            if not user_settings.bot_enabled or not user_settings.alert_horse_race.enabled: return
            search_patterns = [
                r'next race is in \*\*(.+?)\*\*', #English
                r'la siguiente carrera es en \*\*(.+?)\*\*', #Spanish
                r'próxima corrida é em \*\*(.+?)\*\*', #Portuguese
            ]
            timestring_match = await functions.get_match_from_patterns(search_patterns, message_content.lower())
            if not timestring_match:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('Timestring not found in horse race message.', message)
                    return
            timestring = timestring_match.group(1)
            time_left = await functions.calculate_time_left_from_timestring(message, timestring)
            reminder_message = user_settings.alert_horse_race.message.replace('{event}', 'horse race')
            try:
                existing_reminder: reminders.Reminder = await reminders.get_user_reminder(user.id, 'horse-race')
            except exceptions.NoDataFoundError:
                existing_reminder = None
            reminder: reminders.Reminder = (
                await reminders.insert_user_reminder(user.id, 'horse-race', time_left,
                                                    message.channel.id, reminder_message)
            )
            await functions.add_reminder_reaction(message, reminder, user_settings)
            if reminder.record_exists and user_settings.alert_horse_breed.enabled and existing_reminder is None:
                if slash_command:
                    user_command = f"{strings.SLASH_COMMANDS['horse breeding'] or strings.SLASH_COMMANDS['horse race']}"
                else:
                    user_command = '`rpg horse breed` or `rpg horse race`'
                time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, 'horse')
                reminder_message = user_settings.alert_horse_breed.message.replace('{command}', user_command)
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, 'horse', time_left,
                                                         message.channel.id, reminder_message)
                )
            if user_settings.auto_ready_enabled: await functions.call_ready_command(self.bot, message, user)


# Initialization
def setup(bot):
    bot.add_cog(HorseRaceCog(bot))