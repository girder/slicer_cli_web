import pprint
from ctk_cli import CLIArgumentParser


def main(args):
    print('>> parsed arguments')
    pprint.pprint(vars(args))


if __name__ == '__main__':
    main(CLIArgumentParser().parse_args())
