import pprint

from slicer_cli_web import ctk_cli_adjustment  # noqa - imported for side effects
from ctk_cli import CLIArgumentParser


def main(args):
    print('>> parsed arguments')
    print('%r' % args)
    pprint.pprint(vars(args), width=1000)
    with open(args.returnParameterFile, 'w') as f:
        f.write('>> parsed arguments\n')
        f.write('%r\n' % args)
    with open(args.arg1, 'w') as f:
        f.write('example\n')


if __name__ == '__main__':
    main(CLIArgumentParser().parse_args())
