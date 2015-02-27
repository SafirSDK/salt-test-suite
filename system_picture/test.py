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
import os, subprocess, sys, getopt, time, traceback
from socket import gethostname

def log(*args, **kwargs):
  print(*args, **kwargs)
  sys.stdout.flush()

class TestFailure(Exception):
  pass

def run_test():
  log("not doing anything useful yet")
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
  subprocess.check_output(["salt-call", "event.fire_master", str(gethostname(), success), "safir_test"], stderr=subprocess.STDOUT)

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
