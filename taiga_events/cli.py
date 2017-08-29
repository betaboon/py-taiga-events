import argparse
import asyncio
import logging
import os

from . import amqp, signing, websocket


def parseArgs():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        add_help=False
    )
    parser.add_argument("-h", "--websocketHost",
        metavar="HOST",
        type=str,
        default="127.0.0.1",
        help="Host websocket-server should listen on."
    )
    parser.add_argument("-p", "--websocketPort",
        metavar="PORT",
        type=int,
        default=8888,
        help="Port websocket-server should listen on."
    )
    parser.add_argument("-H", "--amqpHost",
        metavar="HOST",
        type=str,
        default="127.0.0.1",
        help="Host to connect to AMQP server."
    )
    parser.add_argument("-P", "--amqpPort",
        metavar="PORT",
        type=int,
        default=5672,
        help="Port to connect to AMQP server."
    )
    parser.add_argument("-V", "--amqpVirtualhost",
        metavar="VHOST",
        type=str,
        default="taiga",
        help="Virtualhost on AMQP server."
    )
    parser.add_argument("--amqpUsername",
        metavar="USERNAME",
        type=str,
        default=os.environ.get('AMQP_USERNAME', None),
        help="Username for AMQP server. Reads from env[AMQP_USERNAME]."
    )
    parser.add_argument("--amqpPassword",
        metavar="PASSWORD",
        type=str,
        default=os.environ.get('AMQP_PASSWORD', None),
        help="Password for AMQP server. Reads from env[AMQP_PASSWORD]."
    )
    parser.add_argument("--signingSalt",
        metavar="SALT",
        type=str,
        default=os.environ.get('SIGNING_SALT', "django.core.signing"),
        help="Salt used for signing. Reads from env[SIGNING_SALT]."
    )
    parser.add_argument("--signingSecret",
        metavar="SECRET",
        type=str,
        default=os.environ.get('SIGNING_SECRET', None),
        help="Secret used for signing. Reads from env[SIGNING_SECRET]."
    )
    parser.add_argument("--pidfile",
        metavar="FILENAME",
        type=str,
        default=None,
        help="Write pidfile"
    )
    parser.add_argument("--help",
        action='help',
        help='show this help message and exit'
    )
    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.INFO)
    args = parseArgs()
    logging.info(args)

    if args.pidfile and os.path.isfile(args.pidfile):
        print("{} already exists, exiting".format(args.pidfile))
        sys.exit()
    elif args.pidfile:
        pid = str(os.getpid())
        file(args.pidfile, 'w').write(pid)

    try:
        signing.setConfig(
            salt=args.signingSalt,
            secret=args.signingSecret
        )

        events = amqp.EventConsumer(
            host=args.amqpHost,
            port=args.amqpPort,
            virtualhost=args.amqpVirtualhost,
            username=args.amqpUsername,
            password=args.amqpPassword
        )

        server = websocket.Server(
            host=args.websocketHost,
            port=args.websocketPort
        )
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(server.serve())
        loop.run_until_complete(events.consume())
        loop.run_forever()
    finally:
        if args.pidfile:
            os.unlink(args.pidfile) 

if __name__ == "__main__":
    main()
