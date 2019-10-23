from ctk_cli import CLIArgumentParser


def main(args):
    print('>> parsed arguments')
    print('%r' % args)


if __name__ == '__main__':
    main(CLIArgumentParser().parse_args())
