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
        opts, args = getopt.getopt(sys.argv[1:], "h:", ["test-script=", "safir-update", "clear-only", "get-logs", "get-results", "help"])
        self.update=False
        self.clear_only=False
        self.get_logs=False
        self.get_results=False
        self.minion_command="*"
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

        if len(args)>0:
            self.minion_command=args[0]
            for a in args[1:]:
                self.minion_command=self.minion_command+" "+a

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
            for root, folders, files in os.walk(src_dir):
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
        log("Running", cmd, args, "on", tgt)
        result = self.client.cmd(tgt,
                                 cmd,
                                 args,
                                 timeout=900, #15 min
                                 expr_form="grain")
        return result

    def salt_get_file(self, tgt, filename):
        if not os.path.isfile(filename):
            raise InternalError("Cannot find file " + filename + " to copy!")
        tgtname = "/home/safir/" + filename
        srcname = "salt://" + os.path.relpath(os.path.join(os.getcwd(),filename), "/home/safir/")
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

    def salt_run_shell_command(self, tgt, command):
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
            raise InternalError("salt_run_shell_command failed for", command)

    def update_linux(self):
        log("    -update Linux minions")
        linux_start_time=time.time()

        log("        delete old debs")
        self.salt_run_shell_command('os:Ubuntu', 'rm -f *.deb')

        log("     uninstalling old packages")
        self.salt_run_shell_command('os:Ubuntu',
                       "sudo apt-get -y purge safir-sdk-core "           +
                                             "safir-sdk-core-tools "     +
                                             "safir-sdk-core-dbg "       +
                                             "safir-sdk-core-testsuite " +
                                             "safir-sdk-core-dev")

        log("        copying packages")
        for pat in ("", "-tools", "-testsuite", "-dev"):
            fullpat = "safir-sdk-core" + pat + "_*_amd64.deb"
            matches = glob.glob(fullpat)
            log(matches)
            if len(matches) != 1:
                raise InternalError("Unexpected number of debs!")
            self.salt_get_file("os:Ubuntu", matches[0])


        raise InternalError("exiting")
        """
        safir_dbg="safir-sdk-core-dbg.deb"
        safir_tools="safir-sdk-core-tools.deb"
        safir_test="safir-sdk-core-testsuite.deb"
        safir_dev="safir-sdk-core-dev.deb"

        self.client.cmd('os:Ubuntu', 'cmd.run',
                                        ['rm -f safir-sdk-core.deb safir-sdk-core-dbg.deb safir-sdk-core-tools.deb safir-sdk-core-dev.deb safir-sdk-core-testsuite.deb'],
                                        expr_form="grain")
        self.client.cmd("os:Ubuntu", "cp.get_file",
                                        ["salt://"+safir_core, "/home/safir/"+safir_core, "makedirs=True"],
                                        timeout=900, #15 min
                                        expr_form="grain")
        #self.client.cmd("os:Ubuntu", "cp.get_file",
        #                                ["salt://"+safir_dbg, "/home/safir/"+safir_dbg, "makedirs=True"],
        #                                timeout=900, #15 min
        #                                expr_form="grain")
        self.client.cmd("os:Ubuntu", "cp.get_file",
                                        ["salt://"+safir_tools, "/home/safir/"+safir_tools, "makedirs=True"],
                                        timeout=900, #15 min
                                        expr_form="grain")
        self.client.cmd("os:Ubuntu", "cp.get_file",
                                        ["salt://"+safir_test, "/home/safir/"+safir_test, "makedirs=True"],
                                        timeout=900, #15 min
                                        expr_form="grain")
        self.client.cmd("os:Ubuntu", "cp.get_file",
                                        ["salt://"+safir_dev, "/home/safir/"+safir_dev, "makedirs=True"],
                                        timeout=900, #15 min
                                        expr_form="grain")


        log("     installing packages")
        self.client.cmd('os:Ubuntu', 'cmd.run', ['sudo dpkg -i ' +
                                                 safir_core + " " +
                                                 safir_tools + " " +
                                                 safir_test + " " +
                                                 safir_dev], expr_form="grain")

        linux_end_time=time.time()
        log("    ...finished after " + str(linux_end_time - linux_start_time) + " seconds")
        """
    def windows_uninstall(self):
        log("     uninstall old Windows installation")
        installpath=r'c:\Program Files\Safir SDK Core'
        uninstaller = installpath + r"\Uninstall.exe"

        self.client.cmd('os:Windows', 'cmd.run', ['"'+uninstaller+'" /S'], timeout=900, expr_form="grain")

        while True:
            res=self.client.cmd("os:Windows", "file.directory_exists", [installpath], timeout=900, expr_form="grain")
            if True not in res.values():
                log("  - Safir SDK Core appears to be uninstalled")
                break
            log("     - Safir SDK Core appears to still be installed")
            time.sleep(1)
        log("     uninstall completed")

    def update_windows(self):
        log("    -update Windows minions")
        safir_win="SafirSDKCore.exe"
        win_start_time=time.time()

        self.windows_uninstall()

        win_end_time=time.time()
        log("    ...uninstall complete after " + str(time.time() - win_start_time) + " seconds")
        log("     Copying installer")
        self.client.cmd("os:Windows",
                        "cp.get_file",
                        ["salt://"+safir_win, "c:/Users/safir/"+safir_win, "makedirs=True"],
                        timeout=1800, #30 min
                        expr_form="grain")
        log("    ...copy complete after " + str(time.time() - win_start_time) + " seconds")

        log("     Running installer")
        result = self.client.cmd('os:Windows',
                                 'cmd.run',
                                 ['c:\\Users\\safir\\'+safir_win+' /S /TESTSUITE'], #Add /NODEVELOPMENT before testsuite to skip dev
                                 timeout=1800, #30 min
                                 expr_form="grain")

        log (result)
        win_end_time=time.time()
        log("    ...finished after " + str(win_end_time - win_start_time) + " seconds")

    def sync_safir(self):
        log("Install latest Safir SDK Core")

        self.update_linux()
        self.update_windows()
        log(" -update Safir finished")

    def upload_test(self):
        abspath = os.path.join(os.getcwd(), self.cmd.test_script_path)
        log("Uploading new test script to minion:", abspath)

        if not abspath.startswith("/home/safir/") or not os.path.isfile(abspath):
            log("Uh oh! Strange script path")
            raise InternalError("Failed to find test script")
        saltpath = "salt://" + abspath[len("/home/safir/"):]
        log(" - using salt path", saltpath)

        while True:
            res = self.client.cmd("os:Ubuntu", "cp.get_file",
                                                        [saltpath, "/home/safir/"+self.cmd.test_script],
                                                        timeout=30*60,
                                                        expr_form="grain")
            if len(set(res.values())) == 1:
                log("Copy test script to ubuntu minions successful")
                break
            log("Copy test script to ubuntu minions failed: ", res)

        while True:
            res = self.client.cmd("os:Windows", "cp.get_file",
                                                        [saltpath, "c:/Users/safir/"+self.cmd.test_script],
                                                        timeout=30*60,
                                                        expr_form="grain")
            if len(set(res.values())) == 1:
                log("Copy test script to windows minions successful")
                break
            log("Copy test script to windows minions failed: ", res)

    def run_test(self):
        log("Run test script on minion")

        node_count=str(len(self.minions))

        self.cmd_iter = self.client.cmd_iter(self.cmd.minion_command,
                                                 "cmd.run",
                                                 ["python " + self.cmd.test_script + " --node-count "+node_count],
                                                 expr_form="compound")

    def collect_result(self):
        log("Collecting result files from minions")
        self.client.cmd("G@os:Ubuntu and "+self.cmd.minion_command,
                                        "cp.push",
                                        ["/home/safir/result.txt"],
                                        expr_form="compound")

        self.client.cmd("G@os:Windows and "+self.cmd.minion_command,
                                        "cp.push",
                                        ["c:/Users/safir/result.txt"],
                                        expr_form="compound")

        self.client.cmd("G@os:Ubuntu and "+self.cmd.minion_command,
                                        "cp.push",
                                        ["/home/safir/result.zip"],
                                        expr_form="compound")

        self.client.cmd("G@os:Windows and "+self.cmd.minion_command,
                                        "cp.push",
                                        ["c:/Users/safir/result.zip"],
                                        expr_form="compound")

        result_dir="test_result"
        if os.path.exists(result_dir):
            shutil.rmtree(result_dir, ignore_errors=True)
            os.makedirs(result_dir)

        for m in self.minions:
            file_found=False
            src_dir=os.path.join("/var/cache/salt/master/minions", m)
            for root, folders, files in os.walk(src_dir):
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
        self.run_test()

        minionResults = dict()
        log("Waiting for results from minions")
        for r in self.cmd_iter:
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
