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

#first wait for one node to go away
while (True):
    output = subprocess.check_output(("salt-run","-t","20","manage.down")).decode("utf-8")

    log("Looking for a rebooting windows node")
    if output.find("minion1") != -1:
        log ("At least one windows node is down, as expected")
        break
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
