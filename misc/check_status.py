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

output = subprocess.check_output(("salt-run","-t","20","manage.down")).decode("utf-8")

print(output)
if output.find("minion") != -1:
    print ("At least one node is down!")
    sys.exit(1)

output = subprocess.check_output(("salt", "--out=json", "*", "cmd.run", "safir_show_config --revision")).decode("utf-8").replace("\n}",",").replace("{","")

output = "{" + output + "}"
print(output)

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
