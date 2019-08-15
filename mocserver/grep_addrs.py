#!/usr/bin/env python3

# grep generated/csr.h for #define name_ADDR 0xe0009014L

import argparse
import collections
import json
import re

from pprint import pprint

def grep_file(filename, regex):

    def_re = re.compile(regex)

    names=[]
    with open(filename) as f:
        for line in f:
            try:
                names.append( def_re.match(line).groupdict())
            except AttributeError as e:
                # AttributeError: 'NoneType' object has no attribute 'group'
                # print(e)
                pass

    # Do we need the address?

    names = [n['name'].split('_') for n in names]

    """
These don't map to the k:k:k:v pattern, so remove the 2nd.
#define CSR_HDMI_IN1_DATA2_CAP_PHASE_ADDR 0xe000d088L
#define CSR_HDMI_IN1_DATA2_CAP_PHASE_RESET_ADDR 0xe000d08cL

#define CSR_SPIFLASH_BITBANG_ADDR 0xe0005000L
#define CSR_SPIFLASH_BITBANG_EN_ADDR 0xe0005008L
"""
    names = [n for n in names if n[-1] not in ['RESET', 'ISSUE', 'EN'] ]

    return names


def test_lines():

    lines = [
            ['a', 'b0', 'c'],
            ['a', 'b0', 'd'],
            ['a', 'b1', 'c'],
            ['a', 'b1', 'd'],
            ['a', 'e', ],
        ]

def mk_obj(lines):

    def make_dict():
        return collections.defaultdict(make_dict);

    the_dict = make_dict()

    def set_path(d, path, value):
        for key in path[:-1]:
            d = d[key]
        d[path[-1]] = value

    for line in lines:
        set_path(the_dict, line, 0)

    return the_dict

def crawl(d):

    # normalize
    # look for in1:v in2:v and change to in:[v,v]

    # are we on a leaf?
    if not hasattr(d,'keys'): return

    # look for fooN keys
    keys=[]
    for k in d:
        crawl(d[k])
        if k in ['FX2']: continue # special cases: fx2 is not a 0,1,2
        if k[-1].isdigit():
            keys.append(k)

    # consolodate them into foo[0,1,2]
    keys.sort()
    for k in keys:
        # grab the value and remove the fooN item
        v=d.pop(k)
        # split into foo and N
        k,n=k[:-1],k[-1]
        # make a foo list
        if n=='0':
            d[k]=[]
        # append all the values to the foo list
        d[k].append(v)

def flatten(o, path=[]):

    if hasattr(o,'keys'):
        for k in o:
            flatten(o[k], path+[k])
    elif type(o)==list:
        for i,o in enumerate(o):
            pathx = path[:-1] + [path[-1]+str(i)]
            flatten(o, pathx)
    else:
        # we are on a leaf
        name = '_'.join(path)
        print("{}: {}".format(name, o))

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file',
            default="build/opsis_hdmi2usb_lm32/software/include/generated/csr.h")

    parser.add_argument('--regex',
        default=r"^#define (?P<name>[\w_]+)_ADDR 0x(?P<addr>[0-9a-f]*)L")
    parser.add_argument('--target',
            default="json")
    return parser.parse_args()

def main():
    args = get_args()

    lines = grep_file(args.file, args.regex)
    # lines = test_lines()

    o = mk_obj(lines)

    crawl(o)

    o=o['CSR']
    # o=o['HDMI']
    if args.target == "json":
        j = json.dumps(o, indent=2)
        print(j)
    elif args.target == "flat":
        flatten(o)


if __name__ == '__main__':
    main()


