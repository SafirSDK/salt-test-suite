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
import os, subprocess, sys, getopt, threading, time, shutil, urllib, glob
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
        log("  run test script kalle.py: master_test_executor --test-script kalle.py")
        log("  clear old files: master_test_executor --clear-only")
        log("  update safir: master_test_executor --safir-update")
        log("  collect log files: master_test_executor --get-logs")
        log("  collect all result files: master_test_executor --get-results")
        sys.exit(1)

    if len(args)>0:
      self.minion_command=args[0]
      for a in args[1:]:
        self.minion_command=self.minion_command+" "+a
#-----------------------------------------------------
# EventHandler - handle when minions are ready
#-----------------------------------------------------
class EventHandler(threading.Thread):
  def __init__(self, num_minions):
    threading.Thread.__init__(self)
    self.event_tag="safir_test"
    self.received=False
    self.num_minions=num_minions
    self.results = dict()

  def run(self):
    ev=salt.utils.event.MasterEvent("/var/run/salt/master")
    for data in ev.iter_events(tag=self.event_tag):
      if data["id"] not in self.results:
        log("Got event from", data["id"], ":", str(data["data"]))
        self.results[data["id"]] = data["data"]
      if len (self.results) == self.num_minions:
          break

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
    log("   Got response from "+str(len(self.minions))+" minions.")
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

    log(" -get logs finished")

  def download_from_jenkins(self):
    subprocess.call(["wget", "-nv", "-O", "/home/safir/deb.zip",
    "http://safir-jenkins-master:8080/safir/job/Build%20master/Config=Release,label=ubuntu-trusty-lts-64-build/lastSuccessfulBuild/artifact/*zip*/archive.zip", "--no-check-certificate"])
    subprocess.call(["wget", "-nv", "-O",
    "/home/safir/win.zip", "http://safir-jenkins-master:8080/safir/job/Build%20master/Config=Release,label=win7-64-vs2013-build/lastSuccessfulBuild/artifact/*zip*/archive.zip", "--no-check-certificate"])

    subprocess.call(["unzip", "-o", "/home/safir/deb.zip", "-d", "/home/safir"])
    subprocess.call(["unzip", "-o", "/home/safir/win.zip", "-d", "/home/safir"])
    os.remove("/home/safir/deb.zip")
    os.remove("/home/safir/win.zip")

    for root, folders, files in os.walk("/home/safir/archive"):
        for f in files:
          dst_file=None
          if f.startswith("safir-sdk-core-testsuite"):
            dst_file="/home/safir/safir-sdk-core-testsuite.deb"
          elif f.startswith("safir-sdk-core-dbg"):
            dst_file="/home/safir/safir-sdk-core-dbg.deb"
          elif f.startswith("safir-sdk-core-dev"):
            dst_file="/home/safir/safir-sdk-core-dev.deb"
          elif f.startswith("safir-sdk-core"):
            dst_file="/home/safir/safir-sdk-core.deb"
          elif f.startswith("SafirSDKCore"):
            dst_file="/home/safir/SafirSDKCore.exe"

          src_file=os.path.join(root, f)
          shutil.copyfile(src_file, dst_file)

    shutil.rmtree("/home/safir/archive", ignore_errors=True)

  def update_linux(self):
    log("  -update Linux minions")
    linux_start_time=time.time()

    safir_core="safir-sdk-core.deb"
    safir_dbg="safir-sdk-core-dbg.deb"
    safir_test="safir-sdk-core-testsuite.deb"
    safir_dev="safir-sdk-core-dev.deb"

    log("    copying packages")
    self.client.cmd('os:Ubuntu', 'cmd.run',
                    ['rm -f safir-sdk-core.deb safir-sdk-core-dbg.deb safir-sdk-core-dev.deb safir-sdk-core-testsuite.deb'],
                    expr_form="grain")
    self.client.cmd("os:Ubuntu", "cp.get_file",
                    ["salt://"+safir_core, "/home/safir/"+safir_core, "makedirs=True"],
                    timeout=900, #15 min
                    expr_form="grain")
    #self.client.cmd("os:Ubuntu", "cp.get_file",
    #                ["salt://"+safir_dbg, "/home/safir/"+safir_dbg, "makedirs=True"],
    #                timeout=900, #15 min
    #                expr_form="grain")
    self.client.cmd("os:Ubuntu", "cp.get_file",
                    ["salt://"+safir_test, "/home/safir/"+safir_test, "makedirs=True"],
                    timeout=900, #15 min
                    expr_form="grain")
    self.client.cmd("os:Ubuntu", "cp.get_file",
                    ["salt://"+safir_dev, "/home/safir/"+safir_dev, "makedirs=True"],
                    timeout=900, #15 min
                    expr_form="grain")

    log("   uninstalling old packages")
    self.client.cmd('os:Ubuntu', 'cmd.run',
                    ['sudo apt-get -y purge safir-sdk-core'],
                    expr_form="grain")
    self.client.cmd('os:Ubuntu', 'cmd.run',
                    ['sudo apt-get -y purge safir-sdk-core-dbg'],
                    expr_form="grain")
    self.client.cmd('os:Ubuntu', 'cmd.run',
                    ['sudo apt-get -y purge safir-sdk-core-testsuite'],
                    expr_form="grain")
    self.client.cmd('os:Ubuntu', 'cmd.run',
                    ['sudo apt-get -y purge safir-sdk-core-dev'],
                    expr_form="grain")

    log("   installing packages")
    self.client.cmd('os:Ubuntu', 'cmd.run', ['sudo dpkg -i '+safir_core], expr_form="grain")
    #self.client.cmd('os:Ubuntu', 'cmd.run', ['sudo dpkg -i '+safir_dbg], expr_form="grain")
    self.client.cmd('os:Ubuntu', 'cmd.run', ['sudo dpkg -i '+safir_test], expr_form="grain")
    self.client.cmd('os:Ubuntu', 'cmd.run', ['sudo dpkg -i '+safir_dev], expr_form="grain")

    linux_end_time=time.time()
    log("  ...finished after " + str(linux_end_time - linux_start_time) + " seconds")

  def windows_uninstall(self):
    log("   uninstall old Windows installation")
    installpath=r'c:\Program Files\Safir SDK Core'
    uninstaller = installpath + r"\Uninstall.exe"

    self.client.cmd('os:Windows', 'cmd.run', ['"'+uninstaller+'" /S'], timeout=900, expr_form="grain")

    snippet="""
import os, time
for x in range(0, 120):
  if not os.path.exists(r'c:\Program Files\Safir SDK Core'):
      break
  time.sleep(5.0)
    """
    res=self.client.cmd("os:Windows", "cmd.exec_code", ["python", snippet], timeout=900, expr_form="grain")
    log("   uninstall completed")

  def update_windows(self):
    log("  -update Windows minions")
    safir_win="SafirSDKCore.exe"
    win_start_time=time.time()

    self.windows_uninstall()

    self.client.cmd("os:Windows", "cp.get_file",
                    ["salt://"+safir_win, "c:/Users/safir/"+safir_win, "makedirs=True"],
                    timeout=900, #15 min
                    expr_form="grain")

    self.client.cmd('os:Windows', 'cmd.run',
                    ['c:\\Users\\safir\\'+safir_win+' /S /TESTSUITE'], #Add /NODEVELOPMENT before testsuite to skip dev
                    timeout=900, #15 min
                    expr_form="grain")

    win_end_time=time.time()
    log("  ...finished after " + str(win_end_time - win_start_time) + " seconds")

  def sync_safir(self):
    log("Install latest Safir SDK Core")

    self.download_from_jenkins()
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

    self.linux_cmd_iter = self.client.cmd_iter("G@os:Ubuntu and "+self.cmd.minion_command,
                                           "cmd.run",
                                           ["python /home/safir/"+self.cmd.test_script+" --node-count "+node_count],
                                           expr_form="compound")

    self.windows_cmd_iter = self.client.cmd_iter("G@os:Windows and "+self.cmd.minion_command,
                                             "cmd.run",
                                             ["python c:\\Users\\safir\\"+self.cmd.test_script+" --node-count "+node_count],
                                             expr_form="compound")

  def collect_result(self):
    log("Collect result")
    self.client.cmd("G@os:Ubuntu and "+self.cmd.minion_command,
                    "cp.push",
                    ["/home/safir/result.txt"],
                    expr_form="compound")

    self.client.cmd("G@os:Windows and "+self.cmd.minion_command,
                    "cp.push",
                    ["c:/Users/safir/result.txt"],
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
      if not file_found:
        log("Found no result file for "+m)


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

    #Start a thread that handles the event when minion has finished the test case
    event_handler=EventHandler(len(self.minions))
    event_handler.start()

    self.upload_test()
    self.run_test()

    #log("Wait for finished signal from the minions")
    #event_handler.join()

    minionOutputs = dict()
    log("Collecting output from Linux minions")
    for r in self.linux_cmd_iter:
      log("got",r)
    #for r in self.client.get_cli_returns(self.linux_jid, minions=set(),tgt="linux", tgt_type="nodegroup", timeout=100):
    #  minionOutputs.update(r)

    #winmin = ("minion10",
               # "minion11",
               # "minion12",
               # "minion13",
               # "minion14",
               # "minion15",
               # "minion16",
               # "minion17",
               # "minion18",
               # "minion19")
    #log("Collecting output from Windows minions")
    #for r in self.client.get_cli_returns(self.windows_jid, minions=set(),tgt="win", tgt_type="nodegroup", timeout=100):
    #  log("got ", r)
    #  minionOutputs.update(r)
    #for m in winmin:
    #  r = list(self.client.get_cli_returns(self.windows_jid, set(m)))
    #  log("got ", m , ":", r)
    #  minionOutputs.update(r)
    #for r in self.client.get_event_iter_returns(self.windows_jid, minions=set(winmin)):
    #  log("got ", r)

    aggregateResult = True
    for minion in sorted(event_handler.results):
      result = event_handler.results[minion]
      log("===============", minion, "returned", result, "== Output: ===============")
      log(minionOutputs[minion]["ret"])
      aggregateResult = result and aggregateResult

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
