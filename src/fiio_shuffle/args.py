from argparse import ArgumentParser

argparser = ArgumentParser("FiiO-shuffle")
argparser.add_argument(
    '--log',
    default='WARNING',
    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
    help='Set the logging level'
)
subparsers = argparser.add_subparsers(title="Tasks", required=True, dest="task")

server_parser = subparsers.add_parser(
    "server",
    help="Start a development server",
    description="""Start web interface. Intended only for development. For
    production, use the provided systemd service.""",
)
server_parser.add_argument("--port", help="Port to bind to. Default: 5000", type=int)
server_parser.add_argument(
    "--host", help="Host to bind to. Default: localhost", type=str
)
server_parser.add_argument(
    "--debug",
    action="store_true",
    help="""
    Enable Flask's debug mode. Major security risk, never use in production!
    """,
)

client_parser = subparsers.add_parser(
    "client",
    help="Submit albums and their covers from a directory",
)
client_parser.add_argument("url", metavar="URL", help="Endpoint to submit to")
client_parser.add_argument("root", metavar="ROOT", help="Filesystem root to use")
