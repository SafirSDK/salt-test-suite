#!/usr/bin/env python2
# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright Consoden AB, 2014-2015 (http://www.consoden.se)
#
# Created by: Joel Ottosson / joel.ottosson@consoden.se
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
import os, subprocess, sys, getopt, time, shutil, glob
import salt.client
import salt.utils.event
from itertools import chain
def log(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()

class InternalError (Exception):
    pass
#-----------------------------------------------------
# Parse command line
#-----------------------------------------------------
class CommandLine:
    def __init__(self):
        opts, _args = getopt.getopt(sys.argv[1:], "h:", ["test-script=", "safir-update", "clear-only", "get-logs", "get-results", "help"])
        self.minion_command="*"
        self.update=False
        self.clear_only=False
        self.get_logs=False
        self.get_results=False
        self.test_script_path=None
        self.test_script=None
        for k, v in opts:
            if k=="--safir-update":
                self.update=True
            elif k=="--clear-only":
                self.clear_only=True
            elif k=="--get-logs":
                self.get_logs=True
            elif k=="--get-results":
                self.get_results=True
            elif k=="--test-script":
                self.test_script_path=v
                self.test_script=os.path.basename(v)

            else:
                log("usage:")
                log("    run test script kalle.py: master_test_executor --test-script kalle.py")
                log("    clear old files: master_test_executor --clear-only")
                log("    update safir: master_test_executor --safir-update")
                log("    collect log files: master_test_executor --get-logs")
                log("    collect all result files: master_test_executor --get-results")
                sys.exit(1)

#-----------------------------------------------------
# Execute test
#-----------------------------------------------------
class Executor:
    def __init__(self):
        #Parse command line
        self.cmd=CommandLine()

        self.client=salt.client.LocalClient()

        #find out which minions are alive
        log("Check that the minions are alive...")
        ping_result=self.client.cmd(self.cmd.minion_command, 'test.ping')
        self.minions=list(ping_result.keys())
        log("     Got response from "+str(len(self.minions))+" minions.")
        if len(self.minions)!=20:
            sys.exit(1)

        self.minions.sort()

        log("Continue test with " + str(len(self.minions)) + " minions")
        for x in self.minions:
            log("'"+x+"'")

    def clear(self):
        if self.cmd.test_script is not None:
            log("Remove old test script from minion")
            self.client.cmd("os:Ubuntu", "cmd.run", ["rm -f /home/safir/"+self.cmd.test_script], expr_form="grain")
            self.client.cmd("os:Windows", "cmd.run", ["del c:\\Users\\safir\\"+self.cmd.test_script], expr_form="grain")

        log("Remove old result.txt from minion")
        self.client.cmd("os:Ubuntu", "cmd.run", ["rm -f /home/safir/result.txt"], expr_form="grain")
        self.client.cmd("os:Windows", "cmd.run", ["del c:\\Users\\safir\\result.txt"], expr_form="grain")

        log("Remove old result files from master")
        shutil.rmtree("test_result/", ignore_errors=True)
        if not os.path.exists("test_result/"):
            os.makedirs("test_result/")

        log("Remove old deb- and exe- files")
        for fl in glob.glob("/home/safir/*.deb"):
            os.remove(fl)
        for fl in glob.glob("/home/safir/*.exe"):
            os.remove(fl)

    def get_logs(self):
        log("Get logs")
        #create zip file of all logs since our version of salt cant push directories
        self.client.cmd("G@os:Ubuntu and "+self.cmd.minion_command,
                                        "cmd.run",
                                        ["zip -qr log.zip ./safir/runtime/log/"],
                                        expr_form="compound")
        self.client.cmd("G@os:Windows and "+self.cmd.minion_command,
                                        "cmd.run",
                                        ['"c:\\Program Files\\7-Zip\\7z" a c:\\Users\\safir\\log.zip -r c:\\Users\\safir\\safir\\runtime\\log'],
                                        expr_form="compound")
        #copy zip file to master
        self.client.cmd("G@os:Ubuntu and "+self.cmd.minion_command,
                                        "cp.push",
                                        ["/home/safir/log.zip"],
                                        expr_form="compound")
        self.client.cmd("G@os:Windows and "+self.cmd.minion_command,
                                        "cp.push",
                                        ["c:\\Users\\safir\\log.zip"],
                                        expr_form="compound")

        log_dir="/home/safir/log"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        for m in self.minions:
            minion_log_dir=os.path.join(log_dir, m)
            if not os.path.exists(minion_log_dir):
                os.makedirs(minion_log_dir)

            file_found=False
            src_dir=os.path.join("/var/cache/salt/master/minions", m)
            for root, _folders, files in os.walk(src_dir):
                for f in files:
                    if f.endswith("log.zip"):
                        src_file=os.path.join(root, f)
                        dst_file=os.path.join(minion_log_dir, "log.zip")
                        shutil.copyfile(src_file, dst_file)
                        os.remove(src_file)
                        file_found=True
            if file_found:
                #unzip the file
                subprocess.call(["unzip", "-o", dst_file, "-d", minion_log_dir])
                os.remove(dst_file)
                log(m+" - logs collected")
            else:
                log(m+" - no logs found")

    def salt_cmd(self, tgt, cmd, args):
        #log("Running", cmd, args, "on", tgt)
        result = self.client.cmd(tgt,
                                 cmd,
                                 args,
                                 timeout=900, #15 min
                                 expr_form="grain")
        return result

    def salt_get_file(self, tgt, filename):
        if not os.path.isfile(filename):
            raise InternalError("Cannot find file " + filename + " to copy!")
        tgtname = ("c:/Users/safir/" if tgt == "os:Windows" else "/home/safir/") + os.path.basename(filename)
        srcname = "salt://" + os.path.relpath(os.path.join(os.getcwd(),filename), "/home/safir/")
        log("[Copying", srcname, "to", tgtname, "on", tgt+ "]")
        result = self.salt_cmd(tgt,"cp.get_file", [srcname, tgtname])
        error = False
        for minion,res in result.items():
            if res != tgtname:
                log("Unexpected result for", minion + ": ", res)
                error = True
        if (tgt == "os:Ubuntu" or tgt == "os:Windows") and len(result) != 10:
            log ("Unexpected number of results in", result)
            raise InternalError("Unexpected number of results: " + str(len(result)))

        if error:
            raise InternalError("salt_get_file failed for", filename)

    def salt_run_shell_command(self, tgt, command, ignore_errors = False):
        log("[Running '"+ command + "' on", tgt + "]")
        results = self.salt_cmd(tgt,"cmd.run_all", [command,])
        error = False
        for minion,result in results.items():
            if result["retcode"] != 0:
                log("Command failed for ", minion + ":", result)
                error = True
        if (tgt == "os:Ubuntu" or tgt == "os:Windows") and len(results) != 10:
            log ("Unexpected number of results in", results)
            raise InternalError("Unexpected number of results: " + str(len(results)))

        if error:
            if ignore_errors:
                log("Ignoring errors")
            else:
                raise InternalError("salt_run_shell_command failed for", command)

    def update_linux(self):
        log("=== Update Linux minions")
        start_time=time.time()

        log("Delete old debs")
        self.salt_run_shell_command('os:Ubuntu', 'rm -f *.deb')

        log("Uninstalling old packages")
        #We uninstall all safir packages, regardless of which ones are installed
        self.salt_run_shell_command('os:Ubuntu',
                       "sudo dpkg --purge safir-sdk-core "           +
                                         "safir-sdk-core-tools "     +
                                         "safir-sdk-core-dev "     +
                                         "safir-sdk-core-dbg "       +
                                         "safir-sdk-core-testsuite ")

        log("Copying packages")
        for pat in ("", "-tools", "-testsuite"):
            fullpat = "safir-sdk-core" + pat + "_*_amd64.deb"
            matches = glob.glob(fullpat)
            if len(matches) != 1:
                raise InternalError("Unexpected number of debs!")
            self.salt_get_file("os:Ubuntu", matches[0])

        log("Installing packages")
        self.salt_run_shell_command('os:Ubuntu', 'sudo dpkg -i *.deb')

        log("finished after " + str(time.time() - start_time) + " seconds")

    def windows_uninstall(self):
        installpath=r'c:\Program Files\Safir SDK Core'
        uninstaller = installpath + r"\Uninstall.exe"

        self.salt_run_shell_command('os:Windows', '"'+uninstaller+'" /S',ignore_errors=True)

        while True:
            res=self.salt_cmd("os:Windows", "file.directory_exists", [installpath])
            if True not in res.values():
                log(" - Safir SDK Core appears to be uninstalled everywhere")
                break
            log(" - Safir SDK Core appears to still be installed somewhere")
            time.sleep(5)

    def update_windows(self):
        log("=== Update Windows minions")
        start_time=time.time()

        log("Uninstall old Windows installation")
        self.windows_uninstall()

        log("Copying installer")
        matches = glob.glob("SafirSDKCore-*.exe")
        if len(matches) != 1:
            raise InternalError("Unexpected number of exes!")
        self.salt_get_file("os:Windows", matches[0])

        log("Running installer")
        #Add /NODEVELOPMENT before testsuite to skip dev
        self.salt_run_shell_command('os:Windows',
                                    matches[0]+' /S /TESTSUITE /NODEVELOPMENT')

        log("finished after " + str(time.time() - start_time) + " seconds")

    def sync_safir(self):
        log("== Install latest Safir SDK Core")
        self.update_linux()
        self.update_windows()
        log("Install latest Safir Core completed")

    def upload_test(self):
        log("Uploading new test script to minions:", self.cmd.test_script_path)
        self.salt_get_file("os:Ubuntu", self.cmd.test_script_path)
        self.salt_get_file("os:Windows", self.cmd.test_script_path)

    def run_test(self):
        log("Run test script on minion")

        node_count=str(len(self.minions))

        cmd_iter = chain \
           (self.client.cmd_iter_no_block("os:Ubuntu",
                                          "cmd.run",
                                          ["python " + self.cmd.test_script + " --node-count "+node_count],
                                          kwarg={"cwd" : "/home/safir"},
                                          expr_form="grain"),
            self.client.cmd_iter_no_block("os:Windows",
                                          "cmd.run",
                                          ["python " + self.cmd.test_script + " --node-count "+node_count],
                                          kwarg={"cwd" : "c:\\Users\\safir\\"},
                                          expr_form="grain"))
        log("Waiting for results from minions")
        while None in cmd_iter:
            time.sleep(1)
        return cmd_iter

    def collect_result(self):
        log("Collecting result files from minions")
        self.client.cmd("G@os:Ubuntu and "+self.cmd.minion_command,
                                        "cp.push",
                                        ["/home/safir/result.txt"],
                                        expr_form="compound")

        self.client.cmd("G@os:Windows and "+self.cmd.minion_command,
                                        "cp.push",
                                        ["c:\\Users\\safir\\result.txt"],
                                        expr_form="compound")

        self.client.cmd("G@os:Ubuntu and "+self.cmd.minion_command,
                                        "cp.push",
                                        ["/home/safir/result.zip"],
                                        expr_form="compound")

        self.client.cmd("G@os:Windows and "+self.cmd.minion_command,
                                        "cp.push",
                                        ["c:\\Users\\safir\\result.zip"],
                                        expr_form="compound")

        result_dir="test_result"
        if os.path.exists(result_dir):
            shutil.rmtree(result_dir, ignore_errors=True)
            os.makedirs(result_dir)

        for m in self.minions:
            file_found=False
            src_dir=os.path.join("/var/cache/salt/master/minions", m)
            for root, _folders, files in os.walk(src_dir):
                for f in files:
                    if f.endswith("result.txt"):
                        src_file=os.path.join(root, f)
                        dst_file=os.path.join(result_dir, m+"_result.txt")
                        shutil.copyfile(src_file, dst_file)
                        os.remove(src_file)
                        file_found=True
                    if f.endswith("result.zip"):
                        src_file=os.path.join(root, f)
                        dst_file=os.path.join(result_dir, m+"_results.zip")
                        shutil.copyfile(src_file, dst_file)
                        os.remove(src_file)
                        file_found=True
            if not file_found:
                log(" - Found no result file for "+m)


    def run(self):
        if self.cmd.get_logs:
            self.get_logs()
            return True

        if self.cmd.get_results:
            self.collect_result()
            return True

        #Run the test script, start clearing old scripts and results
        self.clear()

        if self.cmd.clear_only:
            return True

        if self.cmd.update:
            self.sync_safir()
            return True


        self.upload_test()
        res = self.run_test()

        minionResults = dict()

        for r in res:
            minionResults.update(r)

        aggregateResult = True
        for minion,result in sorted(minionResults.items()):
            retcode = result["retcode"]
            output = result["ret"]
            log("===============", minion, "returned", retcode, "== Output: ===============")
            log(output)
            aggregateResult = (retcode == 0) and aggregateResult

        #If we received a test finished event then collect the result
        self.collect_result()

        return aggregateResult

def main():
    log("===== Start =====")
    try:
        ex=Executor()
        res = ex.run()
        return 0 if res else 1
    except InternalError as e:
        log ("Caught exception: " + str(e))
        return 1
    log("--- Finished! ---")
    return 0

#------------------------------------------------
# If this is the main module, start the program
#------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
