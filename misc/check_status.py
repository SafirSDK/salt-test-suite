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
import subprocess,sys,json,re

def log(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()


def run_command(cmd):
    _proc = subprocess.Popen(cmd,
                            stdout = subprocess.PIPE,
                            stderr = subprocess.STDOUT)

    _output = _proc.communicate()[0].decode("utf-8")
    if _proc.returncode != 0:
        log ("Failed to run command, got returncode", _proc.returncode, "and output:", _output)
        sys.exit(1)
    return _output

log("### Check that all nodes are running ###")
output = run_command(("salt-run","-t","20","manage.down"))
log(output)
if output.find("minion") != -1:
    log ("At least one node is down!")
    sys.exit(1)

log("### Check that all nodes are running as safir user ###")
output = run_command(("salt", "--static", "--out=json", "*", "cmd.run", "whoami"))
log(output)
for minion,s in json.loads(output).items():
    if s != "safir" and s != minion + "\\safir":
        log(minion, "is not running as correct user. Expected safir or",
            minion+"\\safir", "but got", s)
        sys.exit(1)

log("### Check default directory on Linux ###")
output = run_command(("salt", "--static", "--out=json", "-N", "linux", "cmd.run", "pwd"))
log(output)
for minion,s in json.loads(output).items():
    if s != "/home/safir":
        log(minion, "is not running in correct dir. Got", s)
        sys.exit(1)

#check home directory on windows
log("### Check default directory on Windows ###")
output = run_command(("salt", "--static", "--out=json", "-N", "win", "cmd.run", "cd"))
log(output)
for minion,s in json.loads(output).items():
    if s != "C:\\Users\\safir":
        log(minion, "is not running in correct dir. Got", s)
        sys.exit(1)

log("### Check Safir SDK Core version ###")
output = run_command(("salt", "--static", "--out=json", "*", "cmd.run", "safir_show_config --revision"))
log(output)
pattern = re.compile(r"Safir SDK Core Git revision: (.*)")

revisions = set()
for minion,s in json.loads(output).items():
    match = pattern.match(s)
    if match is None:
        log("No revision found for",minion)
        sys.exit(1)
    else:
        log (minion, "has revision", match.group(1))
        revisions.add(match.group(1))

if len(revisions) != 1:
    log("revisions differ between minions")
    sys.exit(1)

log("### Killing test exes on minions ###")
subprocess.call(("salt", "-N", "linux", "cmd.run",
                '"killall -q -9 system_picture_component_test_node communication_test system_picture_listener"'))
subprocess.call(("salt", "-N" ,"win", "cmd.run",
                '"taskkill /f /im communication_test.exe"'))
subprocess.call(("salt", "-N" ,"win", "cmd.run",
                '"taskkill /f /im system_picture_component_test_node.exe"'))
subprocess.call(("salt", "-N" ,"win", "cmd.run",
                '"taskkill /f /im system_picture_listener.exe"'))

sys.exit(0)
