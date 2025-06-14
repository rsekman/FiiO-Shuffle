import logging
from .server import server


def main():
    from .args import argparser

    args = argparser.parse_args()

    log_level = getattr(logging, args.log.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f'Invalid log level: {args.log}')
    logging.basicConfig(level=log_level)

    if args.task == "server":
        server.run(host=args.host, port=args.port, debug=args.debug)
    elif args.task == "client":
        from .client import run_client

        run_client(args.root, args.url)
