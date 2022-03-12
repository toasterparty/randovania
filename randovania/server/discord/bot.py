import discord.ext.commands
from discord_slash import SlashCommand

import randovania


class RandovaniaBot(discord.ext.commands.Bot):
    def __init__(self, configuration: dict):
        super().__init__("%unused-prefix%")
        self.slash = SlashCommand(
            self,
            debug_guild=configuration["debug_guild"],
            sync_commands=True,
        )
        self.configuration = configuration
        self.load_extension("randovania.server.discord.preset_lookup")
        self.load_extension("randovania.server.discord.database_command")
        self.load_extension("randovania.server.discord.faq_command")


def run():
    configuration = randovania.get_configuration()["discord_bot"]

    client = RandovaniaBot(configuration)
    client.run(configuration["token"])
