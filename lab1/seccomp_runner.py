#!/usr/bin/env python3
import argparse
import os
import sys

import pyseccomp as seccomp

parser = argparse.ArgumentParser()
parser.add_argument("--deny", default="mkdir",
                    help="syscall для запрета (EPERM)")
parser.add_argument("cmd", nargs=argparse.REMAINDER,
                    help="команда для запуска (после --)")
args = parser.parse_args()

if not args.cmd:
    print("no command provided", file=sys.stderr)
    sys.exit(2)

f = seccomp.SyscallFilter(defaction=seccomp.ALLOW)
f.add_rule(seccomp.ERRNO(1), args.deny)  # EPERM
f.load()

os.execvp(args.cmd[0], args.cmd)