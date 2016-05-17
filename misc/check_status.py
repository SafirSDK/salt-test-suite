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

def run_command(cmd):
    _proc = subprocess.Popen(cmd,
                            stdout = subprocess.PIPE,
                            stderr = subprocess.STDOUT)

    _output = _proc.communicate()[0].decode("utf-8")
    if _proc.returncode != 0:
        print ("Failed to run command, got returncode", _proc.returncode, "and output:", _output)
        sys.exit(1)
    return _output


output = run_command(("salt-run","-t","20","manage.down"))

print(output)
if output.find("minion") != -1:
    print ("At least one node is down!")
    sys.exit(1)

output = run_command(("salt", "--out=json", "*", "cmd.run", "safir_show_config --revision"))

#due to bugs in salt I had to remove --static above, and fake all the output into a
#single json object like this. If --static starts working again it should just be a
#matter of readding it above and removing these two lines.
output = "{" + output.replace("\n}",",").replace("{","") + "}"
output = output.replace(",\n}","\n}")


pattern = re.compile(r"Safir SDK Core Git revision: (.*)")

revisions = set()
for minion,s in json.loads(output).items():
    match = pattern.match(s)
    if match is None:
        print("No revision found for",minion)
        sys.exit(1)
    else:
        print (minion, "has revision", match.group(1))
        revisions.add(match.group(1))

if len(revisions) != 1:
    print("revisions differ between minions")
    sys.exit(1)
sys.exit(0)
