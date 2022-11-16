from enum import Enum
from typing import Callable
from .tbg_playthrough_state import PlaythroughState

# Conversational words which have no impact on the command parser
FILTER_WORDS = {
    'a'     , 'about', 'all' ,
    'and'   , 'are'  , 'as'  ,
    'at'    , 'be'   , 'but' ,
    'by'    , 'for'  , 'from',
    'had'   , 'have' , 'he'  ,
    'her'   , 'his'  , 'i'   ,
    'in'    , 'is'   , 'it'  ,
    "it's"  , 'its'  , 'my'  ,
    'of'    , 'on'   , 'or'  ,
    'please', 'she'  , 'so'  ,
    'some'  , 'that' , 'the' ,
    'their' , 'them' , 'then',
    'these' , 'they' , 'this',
    'to'    , 'was'  , 'way' ,
    'with'  , 'you'  , 'your',
    'what',
}


class InvalidCommand(Exception):
    pass


class CommandType(Enum):
    HELP = 0,
    EXIT = 1,
    SAVE = 2,
    INVENTORY = 3,
    LOOK = 4,
    INTERACT = 5,
    MOVE = 6,

    def to_class(self):
        if self == self.HELP:
            return CommandHelp
        elif self == self.EXIT:
            return CommandExit
        elif self == self.SAVE:
            return CommandSave
        elif self == self.INVENTORY:
            return CommandInventory
        elif self == self.LOOK:
            return CommandLook
        elif self == self.INTERACT:
            return CommandInteract
        elif self == self.MOVE:
            return CommandMove
        else:
            raise Exception("An internal error occured.")


def _help_message() -> str:
    result = "Supported Commands:"
    for command_type in CommandType:
        result += "\n" + command_type.to_class().help_message()
    return result


class Command:
    """
    Implementation-agnostic interface for all supported commands
    """

    command_data: list[str] | None

    # Child Methods (implement on per-command basis)

    @staticmethod
    def command_type() -> CommandType:
        """
        Returns the command enum corresponding to this class
        """
        raise NotImplementedError("Command not implemented.")

    @staticmethod
    def help_message() -> str:
        """
        Returns the help info specific to this command
        """
        raise NotImplementedError("Command not implemented.")

    @staticmethod
    def from_command_data(command_data: list[str]):
        """
        If the command data is a valid command of this type, return a fresh command instance of that command
        """
        raise NotImplementedError("Command not implemented.")

    def execute(self, state: PlaythroughState, send_message: Callable[[str], None], receive_message: Callable[[], str]) -> str | None:
        """
        Do the work specific to this command, optionally returning a string
        to respond to the user with
        """
        raise NotImplementedError("Command not implemented.")

    # Parent Methods

    def __init__(self, command_data=None) -> None:
        self.command_data = command_data

    def parse_message(message: str) -> list[str]:
        message_data: list[str] = []
        words = message.split(" ")
        for word in words:
            # remove non-alphanumeric
            word = "".join(filter(str.isalnum, word))

            # skip if empty
            if len(word) == 0:
                continue

            # lowercase
            word = word.lower()

            # Filter out meaningless words, but only if they are used in a sentence
            # TODO: could also check for all adverbs in english dictionary
            if word in FILTER_WORDS and len(words) != 1:
                continue

            # it's a valid word
            message_data.append(word)

        if len(message_data) == 0:
            raise InvalidCommand("Pardon?")

        return message_data

    @staticmethod
    def from_message(message: str):
        command_data = Command.parse_message(message)

        for command_type in CommandType:
            command = command_type.to_class().from_command_data(command_data)
            if command:
                return command

        return None


class CommandHelp(Command):
    KEYWORDS = ["help", "h"]

    @staticmethod
    def command_type() -> CommandType:
        return CommandType.HELP

    @staticmethod
    def help_message() -> str:
        return "help - Returns this message"

    @staticmethod
    def from_command_data(command_data: list[str]):
        if command_data[0] in CommandHelp.KEYWORDS:
            return CommandHelp(command_data)

    def execute(self, state: PlaythroughState, send_message: Callable[[str], None], receive_message: Callable[[], str]) -> str | None:
        return _help_message()


class CommandExit(Command):
    KEYWORDS = []

    @staticmethod
    def command_type() -> CommandType:
        return CommandType.EXIT

    @staticmethod
    def help_message() -> str:
        return "tbd"

    @staticmethod
    def from_command_data(command_data: list[str]):
        if command_data[0] in CommandExit.KEYWORDS:
            return CommandExit(command_data)

    def execute(self, state: PlaythroughState, send_message: Callable[[str], None], receive_message: Callable[[], str]) -> str | None:
        return None


class CommandSave(Command):
    KEYWORDS = []

    @staticmethod
    def command_type() -> CommandType:
        return CommandType.SAVE

    @staticmethod
    def help_message() -> str:
        return "tbd"

    @staticmethod
    def from_command_data(command_data: list[str]):
        if command_data[0] in CommandSave.KEYWORDS:
            return CommandSave(command_data)

    def execute(self, state: PlaythroughState, send_message: Callable[[str], None], receive_message: Callable[[], str]) -> str | None:
        return None


class CommandInventory(Command):
    KEYWORDS = ["i", "inventory", "inv", "inven", "items", "list", "pickups"]

    @staticmethod
    def command_type() -> CommandType:
        return CommandType.INVENTORY

    @staticmethod
    def help_message() -> str:
        return "inventory - Examines your current inventory"

    @staticmethod
    def from_command_data(command_data: list[str]):
        if command_data[0] in CommandInventory.KEYWORDS:
            return CommandInventory(command_data)

    def execute(self, state: PlaythroughState, send_message: Callable[[str], None], receive_message: Callable[[], str]) -> str | None:
        return state.describe_inventory()


class CommandLook(Command):
    KEYWORDS = []

    @staticmethod
    def command_type() -> CommandType:
        return CommandType.LOOK

    @staticmethod
    def help_message() -> str:
        return "tbd"

    @staticmethod
    def from_command_data(command_data: list[str]):
        if command_data[0] in CommandLook.KEYWORDS:
            return CommandLook(command_data)

    def execute(self, state: PlaythroughState, send_message: Callable[[str], None], receive_message: Callable[[], str]) -> str | None:
        return None


class CommandInteract(Command):
    KEYWORDS = []

    @staticmethod
    def command_type() -> CommandType:
        return CommandType.INTERACT

    @staticmethod
    def help_message() -> str:
        return "tbd"

    @staticmethod
    def from_command_data(command_data: list[str]):
        if command_data[0] in CommandInteract.KEYWORDS:
            return CommandInteract(command_data)

    def execute(self, state: PlaythroughState, send_message: Callable[[str], None], receive_message: Callable[[], str]) -> str | None:
        return None


class CommandMove(Command):
    KEYWORDS = []

    @staticmethod
    def command_type() -> CommandType:
        return CommandType.MOVE

    @staticmethod
    def help_message() -> str:
        return "tbd"

    @staticmethod
    def from_command_data(command_data: list[str]):
        if command_data[0] in CommandMove.KEYWORDS:
            return CommandMove(command_data)

    def execute(self, state: PlaythroughState, send_message: Callable[[str], None], receive_message: Callable[[], str]) -> str | None:
        return None

# TODO: logbook/journal/diary command for hints, completed events, etc.
