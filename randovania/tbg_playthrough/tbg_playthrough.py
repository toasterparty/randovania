import sys
import os
from pathlib import Path
from typing import Callable

from .tbg_playthrough_commands import InvalidCommand, CommandType, Command
from .tbg_playthrough_state import PlaythroughState

def _cli_receive_message() -> str:
    return input("> ")


def _cli_send_message(message: str) -> None:
    return print(f"\n{message}\n\n", end="")


class Playthrough:
    rdvgame: Path
    send_message: Callable[[str], None]
    receive_message: Callable[[], str]
    playthrough_state: PlaythroughState

    def __init__(self, rdvgame: Path, send_message: Callable, receive_message: Callable) -> None:
        self.rdvgame = rdvgame
        self.send_message = send_message
        self.receive_message = receive_message
    
    def load_rdvgame(self, rdvgame: Path) -> None:
        self.playthrough_state = PlaythroughState.from_rdvgame(rdvgame)
        self.send_message(f"Successfully started new game: {self.playthrough_state.configuration.game.long_name} - {self.playthrough_state.description.shareable_word_hash} ({self.playthrough_state.description.shareable_hash})")

        # TODO: Prolog text

    def _process_one_message(self) -> None:
        message = self.receive_message()
        if not message.isascii():
            raise InvalidCommand("I'm sorry, there are illegal characters in your command.")
        command: Command = Command.from_message(message)
        if command is None:
            raise InvalidCommand(
                "Sorry, I don't understand that command. Say 'help' for the list of commands I recognize.")

        response = command.execute(self.playthrough_state, self.send_message, self.receive_message)
        if response:
            self.send_message(response)

    def do_playthrough_forever(self) -> None:
        while (True):
            try:
                self._process_one_message()
            except KeyboardInterrupt:
                self.send_message("\nKeyboard Interrupt detected. Exiting...")
                return
            except InvalidCommand as e:
                self.send_message(f"{e}")
            except Exception as e:
                exc_type, _, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                self.send_message(f"\n{e}\n{exc_type} - {fname}:{exc_tb.tb_lineno}")

    # TODO: do_playthrough_forever_async


def begin_playthrough(rdvgame: Path, send_message: Callable = _cli_send_message,
                      receive_message: Callable = _cli_receive_message) -> None:
    playthrough = Playthrough(rdvgame, send_message, receive_message)
    playthrough.load_rdvgame(rdvgame)
    playthrough.do_playthrough_forever()
