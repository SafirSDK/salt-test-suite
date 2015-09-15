#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright Consoden AB, 2015 (http://www.consoden.se)
#
# Created by: Lars Hagstrom / lars.hagstrom@consoden.se
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
import subprocess,sys,json,re, time

def log(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()

output = subprocess.check_output(("salt-run","-t","20","manage.down")).decode("utf-8")

if output.find("minion1") != -1:
    log ("At least one windows node is down:")
    log (output)
    log ("Will reboot the others, though.")
else:
    log ("All windows nodes appear to be up. Will reboot them!")

subprocess.check_output(("salt", "-N", "win", "system.reboot"))

#first wait for all windows nodes to go away
needed = set(["minion10","minion11","minion12","minion13","minion14","minion15","minion16","minion17","minion18","minion19"])
while (True):
    output = subprocess.check_output(("salt-run","-t","20","manage.down")).decode("utf-8").replace("- ","")

    needed = needed - set(output.splitlines())
    if len(needed) == 0:
        log("All windows nodes appear to have gone away, as expected")
        break
    else:
        log("Still waiting for some nodes to go away:")
        log(needed)
    time.sleep(1)

#then wait for all to come up again
while (True):
    output = subprocess.check_output(("salt-run","-t","20","manage.down")).decode("utf-8")

    log("Checking if all windows nodes are up again.")

    if output.find("minion1") == -1:
        log ("No windows nodes down!")
        break
    else:
        log( "Nodes that are down:")
        log(output)
    time.sleep(1)

sys.exit(0)
