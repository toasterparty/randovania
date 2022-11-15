from pathlib import Path
from typing import Callable
from multiprocessing import Process


def _cli_receive_message() -> str:
    return input("> ")


def _cli_send_message(message: str) -> None:
    return print(f"\n{message}\n\n", end="")


class InvalidCommand(Exception):
    pass


class Playthrough:
    rdvgame: Path
    send_message: Callable
    receive_message: Callable

    def __init__(self, rdvgame: Path, send_message: Callable, receive_message: Callable) -> None:
        self.rdvgame = rdvgame
        self.send_message = send_message
        self.receive_message = receive_message

    def _sanatize_message(self, message: str) -> str:
        if not message.isascii():
            raise InvalidCommand("I'm sorry, there are illegal characters in your command.")
        return message.strip().lower()

    def _process_one_message(self) -> None:
        message = self._sanatize_message(self.receive_message())
        # self.send_message(f"Received: {message}")

    def do_playthrough_forever(self) -> None:
        self.send_message(f"Playthrough of {self.rdvgame} started!")

        while (True):
            try:
                self._process_one_message()
            except KeyboardInterrupt:
                self.send_message("\nKeyboard Interrupt detected. Exiting...")
                return
            except Exception as e:
                self.send_message(f"\n{e}")

    # TODO: do_playthrough_forever_async


def begin_playthrough(rdvgame: Path, send_message: Callable = _cli_send_message,
                      receive_message: Callable = _cli_receive_message) -> None:
    playthrough = Playthrough(rdvgame, send_message, receive_message)
    playthrough.do_playthrough_forever()
