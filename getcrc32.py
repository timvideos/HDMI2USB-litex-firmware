#!/usr/bin/env python3

import os
import argparse
import binascii

def main():
    parser = argparse.ArgumentParser(description="Print file length and CRC32.")
    parser.add_argument("-n", help="List filenames of input files.")
    parser.add_argument("-l", help="List length of input files.")
    parser.add_argument("files", metavar="f", type=str, nargs="+",
        help="Files to calculate CRC32")

    args = parser.parse_args()

    lens = []
    crcs = []
    for f in args.files:
        lens.append(os.path.getsize(f))
        with open(f, "rb") as fp:
            crcs.append(binascii.crc32(fp.read()))

    for n in range(len(args.files)):
        print("{}: {} {:#0X}".format(args.files[n], lens[n], crcs[n]))




if __name__ == "__main__":
    main()
