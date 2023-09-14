from .server import server


def main():
    from .args import argparser

    args = argparser.parse_args()
    if args.task == "server":
        server.run(host=args.host, port=args.port, debug=args.debug)
    elif args.task == "client":
        from .client import run_client

        run_client(args.root, args.url)
