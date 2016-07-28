#!/usr/bin/env python2
# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright Consoden AB, 2015 (http://www.consoden.se)
#
# Created by: Lars Hagström / lars.hagstrom@consoden.se
#
###############################################################################
#
# This file is part of Safir SDK Core.
#
# Safir SDK Core is free software: you can redistribute it and/or modify
# it under the terms of version 3 of the GNU General Public License as
# published by the Free Software Foundation.
#
# Safir SDK Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Safir SDK Core.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from __future__ import print_function
import subprocess, sys, re, socket

NODES_PER_COMPUTER = 1
#COMPUTERS=[0,1,2,3,4,5,10,11,12,13,14,15]
COMPUTERS=list(range(10))
REVOLUTIONS = 3

def log(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()


class TestFailure(Exception):
    pass


def mynum():
    num = re.match(r"minion([0-9][0-9])",socket.gethostname()).group(1)
    return int(num)

def gethostname():
    #hostname = socket.gethostname()
    #return hostname + "-test"
    return "192.168.66.1{0:02d}".format(mynum())

def seedip():
    return "192.168.66.1{0:02d}".format(COMPUTERS[0])

def run_test():
    if mynum() not in COMPUTERS:
        log("not running on this node")
        return

    num = COMPUTERS.index(mynum())
    args = ("--start", str(num * NODES_PER_COMPUTER),
            "--nodes", str(NODES_PER_COMPUTER),
            "--total-nodes", str(len(COMPUTERS) * NODES_PER_COMPUTER),
            "--own-ip", gethostname(),
            "--seed-ip", seedip(),
            "--revolutions", str(REVOLUTIONS),
            "--only-control",
            "--zip-results")
    log("Starting circular_restart.py with arguments",args)
    if sys.platform == "win32":
        ret = subprocess.call(("circular_restart.py",) + args, shell = True)
    else:
        ret = subprocess.call(("circular_restart",) + args)

    log("circular_restart.py exited with code", ret)
    if ret != 0:
        raise TestFailure("circular_restart.py failed")

def main():
    success = False
    try:
        run_test()
        success = True
    except TestFailure as e:
        log ("Error: " + str(e))
    except Exception as e:
        log ("Caught exception: " + str(e))

    if success:
        log("Test was successful")
        return 0
    else:
        log("Test failed")
        return 1

#------------------------------------------------
# If this is the main module, start the program
#------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
