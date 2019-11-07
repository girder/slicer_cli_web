import argparse
import os
from time import sleep
import pprint
import sys

from progress_helper import ProgressHelper


def main(args):
    with ProgressHelper('main', 'test') as p:
        p.progress(0.1)
        print('>> parsed arguments')
        for i in range(10):
            sleep(2)
            p.progress(i / 10.)
        pprint.pprint(vars(args))


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--json':
        json_spec_file = os.path.splitext(sys.argv[0])[0] + '.json'
        with open(json_spec_file) as f:
            print(f.read())
        sys.exit(0)

    parser = argparse.ArgumentParser()
    parser.add_argument('--count', dest='count', type=int, default=10)
    parser.add_argument('--sleep', dest='sleep', type=int, default=1)

    args = parser.parse_args()
    with ProgressHelper('example', 'sleeping mostly') as p:
        for i in range(args.count):
            print('doing some complicated things...')
            p.progress(float(i) / args.count)
            sleep(args.sleep)
        p.progress(1)
