from enum import Enum
from typing import Callable
from .tbg_playthrough_state import PlaythroughState
from . import InvalidCommand, sanatize_text, FILTER_WORDS


class CommandType(Enum):
    HELP = 0,
    EXIT = 1,
    INVENTORY = 2,
    LOOK = 3,
    INTERACT = 4,
    MOVE = 5,

    def to_class(self):
        if self == self.HELP:
            return CommandHelp
        elif self == self.EXIT:
            return CommandExit
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
    def from_command_data(command_data: list[str], state: PlaythroughState):
        """
        If the command data is a valid command of this type, return a fresh command instance of that command
        """
        raise NotImplementedError("Command not implemented.")

    def execute(
            self, state: PlaythroughState, send_message: Callable[[str],
                                                                  None],
            receive_message: Callable[[],
                                      str]) -> str | None:
        """
        Do the work specific to this command, optionally returning a string
        to respond to the user with
        """
        raise NotImplementedError("Command not implemented.")

    # Parent Methods

    def __init__(self, command_data=None) -> None:
        self.command_data = command_data

    def parse_message(message: str) -> list[str]:
        message = sanatize_text(message, filter_words=True)
        return message.split(" ")

    @staticmethod
    def from_message(message: str, state: PlaythroughState):
        command_data = Command.parse_message(message)

        for command_type in CommandType:
            command = command_type.to_class().from_command_data(command_data, state)
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
    def from_command_data(command_data: list[str], state: PlaythroughState):
        if command_data[0] in CommandHelp.KEYWORDS:
            return CommandHelp(command_data)

    def execute(
            self, state: PlaythroughState, send_message: Callable[[str],
                                                                  None],
            receive_message: Callable[[],
                                      str]) -> str | None:
        return _help_message()


class CommandExit(Command):
    KEYWORDS = []

    @staticmethod
    def command_type() -> CommandType:
        return CommandType.EXIT

    @staticmethod
    def help_message() -> str:
        return "exit - [NYI]"

    @staticmethod
    def from_command_data(command_data: list[str], state: PlaythroughState):
        if command_data[0] in CommandExit.KEYWORDS:
            return CommandExit(command_data)

    def execute(
            self, state: PlaythroughState, send_message: Callable[[str],
                                                                  None],
            receive_message: Callable[[],
                                      str]) -> str | None:
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
    def from_command_data(command_data: list[str], state: PlaythroughState):
        if command_data[0] in CommandInventory.KEYWORDS:
            return CommandInventory(command_data)

    def execute(
            self, state: PlaythroughState, send_message: Callable[[str],
                                                                  None],
            receive_message: Callable[[],
                                      str]) -> str | None:
        return state.describe_inventory()


class CommandLook(Command):
    KEYWORDS = ["look", "l", "room", "area", "here", "describe", "observe", "check", "where"]

    @staticmethod
    def command_type() -> CommandType:
        return CommandType.LOOK

    @staticmethod
    def help_message() -> str:
        return "look - Inspect the local area by sight"

    @staticmethod
    def from_command_data(command_data: list[str], state: PlaythroughState):
        if command_data[0] in CommandLook.KEYWORDS:
            return CommandLook(command_data)

    def execute(
            self, state: PlaythroughState, send_message: Callable[[str],
                                                                  None],
            receive_message: Callable[[],
                                      str]) -> str | None:
        return state.describe_here()


class CommandInteract(Command):
    KEYWORDS = ["use", "collect", "take", "pickup", "interact", "get", "inspect", "kill",
                "investigate", "acquire", "fight", "destroy", "solve", "battle", "combat", "engage", "complete", "do", "defeat"]

    @staticmethod
    def command_type() -> CommandType:
        return CommandType.INTERACT

    @staticmethod
    def help_message() -> str:
        return "use - Interact with an object or event in the area"

    @staticmethod
    def from_command_data(command_data: list[str], state: PlaythroughState):
        if command_data[0] in CommandInteract.KEYWORDS:
            return CommandInteract(command_data)

    def execute(
            self, state: PlaythroughState, send_message: Callable[[str],
                                                                  None],
            receive_message: Callable[[],
                                      str]) -> str | None:
        return state.interact(self.command_data, send_message, receive_message)


class CommandMove(Command):
    KEYWORDS = ["go", "move", "enter", "travel", "traverse", "into", "proceede"]

    @staticmethod
    def command_type() -> CommandType:
        return CommandType.MOVE

    @staticmethod
    def help_message() -> str:
        return "go - Move to another room/area/world etc. Some games support cardinal directions (n/s/e/w)"

    @staticmethod
    def from_command_data(command_data: list[str], state: PlaythroughState):
        throw_error = False
        if command_data[0] in CommandMove.KEYWORDS:
            if len(command_data) < 2:
                raise InvalidCommand("Where do you want to go?")
            command_data.pop(0)
            throw_error = True

        desired = command_data.pop(0)
        for word in command_data:
            desired += " " + word

        # Handle cardinal directions
        if desired in ["n", "s", "e", "w", "north", "south", "east", "west"]:
            return CommandMove(desired)

        actual_room_name = None
        # Strip conversational words out of the room names
        for room in state.get_connected_rooms():
            real_room_name = room
            room = room.lower()
            for word in FILTER_WORDS:
                room = room.removeprefix(f"{word} ").removesuffix(f" {word}").replace(f" {word} ", " ")

            if desired != room:
                continue

            actual_room_name = real_room_name

            break

        if actual_room_name:
            return CommandMove(actual_room_name)

        if throw_error:
            raise InvalidCommand(f"I don't understand how you would get to {desired.title()} from here.")

        return None

    def execute(
            self, state: PlaythroughState, send_message: Callable[[str],
                                                                  None],
            receive_message: Callable[[],
                                      str]) -> str | None:
        result = state.go_to_room(self.command_data, send_message, receive_message)
        if result:
            send_message(result)
        return CommandLook().execute(state, send_message, receive_message)

# TODO: logbook/journal/diary command for hints, completed events, etc.
