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
import os, subprocess, sys, getopt, time, traceback, re, socket, time

NODES_PER_COMPUTER = 1
LINUX_ONLY = False
WINDOWS_ONLY = False
COMPUTERS = 10 + (0 if LINUX_ONLY or WINDOWS_ONLY else 10)

def log(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()

class TestFailure(Exception):
    pass


def mynum():
    num = re.match(r"minion([0-9][0-9])",socket.gethostname()).group(1)
    return int(num)

def gethostname():
    hostname = socket.gethostname()
    #return hostname + "-test"
    return "192.168.66.1{0:02d}".format(mynum())

def seedip():
    if WINDOWS_ONLY:
        return "192.168.66.110"
    else:
        return "192.168.66.100"

def run_test():
    if sys.platform == "win32":
        if LINUX_ONLY:
            log("not running on windows")
            return
    else:
        if WINDOWS_ONLY:
            log("not running on linux")
            return

    num = mynum() - (10 if WINDOWS_ONLY else 0)
    args = ("--start", str(num * NODES_PER_COMPUTER),
            "--nodes", str(NODES_PER_COMPUTER),
            "--total-nodes", str(COMPUTERS * NODES_PER_COMPUTER),
            "--own-ip", gethostname(),
            "--seed-ip", seedip(),
            "--revolutions", str(3))
    log("Starting circular_restart.py with arguments",args)
    if sys.platform == "win32":
        ret = subprocess.call(("circular_restart.py",) + args, shell = True)
    else:
        ret = subprocess.call(("circular_restart",) + args)

    log("circular_restart.py exited with code", ret)
    if ret != 0:
        raise TestFailure("circular_restart.py failed")

def main():
    startdelay = max(0,mynum()-(10 if WINDOWS_ONLY else 0)) * 10

    log("Sleeping", startdelay, "seconds before starting test apps")
    time.sleep(startdelay)
    success = False
    try:
      run_test()
      success = True
    except TestFailure as e:
      log ("Error: " + str(e))
    except Exception as e:
      log ("Caught exception: " + str(e))

    #send the event multiple times, to reduce risk of it getting lost
    for i in range(10):
        subprocess.check_output(["salt-call", "event.fire_master", str(success), "safir_test"], stderr=subprocess.STDOUT)
        time.sleep(0.5)

    if success:
      log("Test was successful")
    else:
      log("Test failed")

#------------------------------------------------
# If this is the main module, start the program
#------------------------------------------------
if __name__ == "__main__":
    main()
    sys.exit(0)
