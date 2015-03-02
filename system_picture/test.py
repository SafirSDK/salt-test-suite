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
import os, subprocess, sys, getopt, time, traceback, re
from socket import gethostname

def log(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()

class TestFailure(Exception):
    pass

def mynum():
    num = re.match(r"minion([0-9][0-9])",gethostname).group(1))
    return int(num)

def prevhostname():
    num = mynum() + 1
    if num > 9
        num = 0
    return "minion{0:02d}".format(num)

def run_test():
    if sys.platform == "win32":
        return

    args = ("--start", str(mynum() * 3),
            "--nodes", str(3),
            "--total-nodes", str(30),
            "--own-ip", gethostname(),
            "--prev-ip", prevhostname())
    log(args)
    #signal that we are done

def main():
    success = False
    try:
      run_test()
      success = True
    except TestFailure as e:
      log ("Error: " + str(e))
    except Exception as e:
      log ("Caught exception: " + str(e))

    #do we need this?
    subprocess.check_output(["salt-call", "event.fire_master", str(success), "safir_test"], stderr=subprocess.STDOUT)

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
