from argparse import ArgumentParser
from pathlib import Path


def create_subparsers(sub_parsers):
    parser: ArgumentParser = sub_parsers.add_parser(
        "playthrough",
        help="Play a seed as a text based advengure game"
    )

    parser.add_argument(
        "--rdvgame",
        type=Path,
        help="Path of seed to play",
    )

    # TODO: rdvtbg path to load save file (mutually exclusive w/ above)

    def tbg_command_logic(args):
        from randovania.tbg_playthrough.tbg_playthrough import begin_playthrough
        if args.rdvgame is None:

            # TODO: File picker for rdvgame or save file

            parser.print_help()
            raise SystemExit(1)
        begin_playthrough(args.rdvgame)

    parser.set_defaults(func=tbg_command_logic)
