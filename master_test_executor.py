#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, subprocess, sys, getopt, threading, time, shutil, urllib, glob
import salt.client
import salt.utils.event

#-----------------------------------------------------
# Parse command line
#-----------------------------------------------------
class CommandLine:
  def __init__(self):
    opts, args = getopt.getopt(sys.argv[1:], "h:", ["test-script=", "safir-update", "clear-only", "get-logs", "help"])
    self.update=False
    self.clear_only=False
    self.get_logs=False
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
      elif k=="--test-script":
        self.test_script_path=v
        self.test_script=os.path.basename(v)

      else:
        print("usage:")
        print("  run test script kalle.py: master_test_executor --test-script kalle.py")
        print("  clear old files: master_test_executor --clear-only")
        print("  update safir: master_test_executor --safir-update")
        print("  collect log files: master_test_executor --get-logs")
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

  def run(self):
    ev=salt.utils.event.MasterEvent("/var/run/salt/master")
    num_events=0
    for data in ev.iter_events(tag=self.event_tag):
      print("Got event from "+data["id"])
      num_events=num_events+1
      if num_events==self.num_minions:
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
    print("Check that the minions are alive...")
    for tries in range(0,3):
      ping_result=self.client.cmd(self.cmd.minion_command, 'test.ping')
      self.minions=list(ping_result.keys())
      print("   Got response from "+str(len(self.minions))+" minions.")
      if len(self.minions)!=20:
        print("   Try again to wake up the non-responding minions...")
      else:
        print("   All minions responded!")
        break
  
    self.minions.sort()
    
    print("Continue test with " + str(len(self.minions)) + " minions")
    for x in self.minions:
      print("'"+x+"'")      

  def clear(self):
    if self.cmd.test_script is not None:
      print("Remove old test script from minion")
      self.client.cmd("os:Ubuntu", "cmd.run", ["rm -f /home/safir/"+self.cmd.test_script], expr_form="grain")
      self.client.cmd("os:Windows", "cmd.run", ["del c:\\Users\\safir\\"+self.cmd.test_script], expr_form="grain")
    
    print("Remove old result.txt from minion")    
    self.client.cmd("os:Ubuntu", "cmd.run", ["rm -f /home/safir/result.txt"], expr_form="grain")
    self.client.cmd("os:Windows", "cmd.run", ["del c:\\Users\\safir\\result.txt"], expr_form="grain")
    
    print("Remove old result files from master")
    shutil.rmtree("/home/safir/test_result/", ignore_errors=True)
    if not os.path.exists("/home/safir/test_result/"):
      os.makedirs("/home/safir/test_result/")
    
    print("Remove old deb- and exe- files")
    for fl in glob.glob("/home/safir/*.deb"):
      os.remove(fl)
    for fl in glob.glob("/home/safir/*.exe"):
      os.remove(fl)
      
  def get_logs(self):
    print("Get logs")
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
        print(m+" - logs collected")
      else:
        print(m+" - no logs found")
                    
    print(" -get logs finished")
    
  def download_from_jenkins(self):
    subprocess.call(["wget", "-O", "/home/safir/deb.zip",
    "https://10.0.0.107/safir/job/Project%20Stewart/Config=Release,label=ubuntu-trusty-lts-64-build/lastSuccessfulBuild/artifact/*zip*/archive.zip", "--no-check-certificate"])
    subprocess.call(["wget", "-O",
    "/home/safir/win.zip", "https://10.0.0.107/safir/job/Project%20Stewart/Config=Release,label=win7-64-vs2013-build/lastSuccessfulBuild/artifact/*zip*/archive.zip", "--no-check-certificate"])
    
    subprocess.call(["unzip", "-o", "/home/safir/deb.zip", "-d", "/home/safir"])
    subprocess.call(["unzip", "-o", "/home/safir/win.zip", "-d", "/home/safir"])
    os.remove("/home/safir/deb.zip")
    os.remove("/home/safir/win.zip")
    
    for root, folders, files in os.walk("/home/safir/archive"):
        for f in files:
          dst_file=None
          if f.startswith("safir-sdk-core-testsuite"):
            dst_file="/home/safir/safir-sdk-core-testsuite.deb"
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
    print("  -update Linux minions")
    linux_start_time=time.time()
    
    safir_core="safir-sdk-core.deb"
    safir_test="safir-sdk-core-testsuite.deb"
    safir_dev="safir-sdk-core-dev.deb"
    
    self.client.cmd("os:Ubuntu", "cp.get_file",
                    ["salt://"+safir_core, "/home/safir/"+safir_core, "makedirs=True"],
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

    print("   installing packages")
    self.client.cmd('os:Ubuntu', 'cmd.run',
                    ['sudo apt-get -y purge safir-sdk-core safir-sdk-core-testsuite safir-sdk-core-dev'],
                    expr_form="grain")
    self.client.cmd('os:Ubuntu', 'cmd.run', ['sudo dpkg -i '+safir_core], expr_form="grain")
    self.client.cmd('os:Ubuntu', 'cmd.run', ['sudo dpkg -i '+safir_test], expr_form="grain")
    self.client.cmd('os:Ubuntu', 'cmd.run', ['sudo dpkg -i '+safir_dev], expr_form="grain")

    linux_end_time=time.time()
    print("  ...finished after " + str(linux_end_time - linux_start_time) + " seconds")
        
  def windows_uninstall(self):
    print("   uninstall old Windows installation")
    installpath=r'c:\Program Files\Safir SDK Core'
    uninstaller = installpath + r"\Uninstall.exe"
    
    self.client.cmd('os:Windows', 'cmd.run', ['"'+uninstaller+'" /S'], expr_form="grain")
    
    snippet="""
import os, time
for x in range(0, 120):
  if not os.path.exists(r'c:\Program Files\Safir SDK Core'):
      break
  time.sleep(5.0)
    """
    res=self.client.cmd("os:Windows", "cmd.exec_code", ["python", snippet], expr_form="grain")
    print(res)
    print("done")
        
  def update_windows(self):
    print("  -update Windows minions")
    safir_win="SafirSDKCore.exe"
    win_start_time=time.time()
    self.client.cmd("os:Windows", "cp.get_file",
                    ["salt://"+safir_win, "c:/Users/safir/"+safir_win, "makedirs=True"],
                    timeout=900, #15 min
                    expr_form="grain")

    #self.windows_uninstall()
    
    self.client.cmd('os:Windows', 'cmd.run',
                    ['c:\\Users\\safir\\'+safir_win+' /S /NODEVELOPMENT /TESTSUITE'], expr_form="grain")
                
    win_end_time=time.time()
    print("  ...finished after " + str(win_end_time - win_start_time) + " seconds")
    
  def sync_safir(self):
    print("Install latest Safir SDK Core")
    #self.update_windows()
    self.windows_uninstall()
    """
    self.download_from_jenkins()
    self.update_linux()
    self.update_windows()
    print(" -update Safir finished")
    """

  def upload_test(self):
    print("Upload new test script to minion")
    self.client.cmd("os:Ubuntu", "cp.get_file",
                    ["salt://salt-test-suite/"+self.cmd.test_script_path, "/home/safir/"+self.cmd.test_script],
                    expr_form="grain")
    self.client.cmd("os:Windows", "cp.get_file",
                    ["salt://salt-test-suite/"+self.cmd.test_script_path, "c:/Users/safir/"+self.cmd.test_script],
                    expr_form="grain")
        
  def run_test(self):
    print("Run test script on minion")

    node_count=str(len(self.minions))
    
    self.client.cmd_async("G@os:Ubuntu and "+self.cmd.minion_command,
                    "cmd.run",
                    ["python /home/safir/"+self.cmd.test_script+" --node-count "+node_count],
                    expr_form="compound")    
    
    self.client.cmd_async("G@os:Windows and "+self.cmd.minion_command,
                    "cmd.run",
                    ["python c:\\Users\\safir\\"+self.cmd.test_script+" --node-count "+node_count],
                    expr_form="compound")

  def collect_result(self):
    print("Collect result")
    self.client.cmd("G@os:Ubuntu and "+self.cmd.minion_command,
                    "cp.push",
                    ["/home/safir/result.txt"],
                    expr_form="compound")
                    
    self.client.cmd("G@os:Windows and "+self.cmd.minion_command,
                    "cp.push",
                    ["c:/Users/safir/result.txt"],
                    expr_form="compound")

    result_dir="/home/safir/test_result"
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
        print("Found no result for "+m)

    
  def run(self):
    if self.cmd.get_logs:
      self.get_logs()
      return
  
    #Run the test script, start clearing old scripts and results
    self.clear()
    
    if self.cmd.clear_only:
      return
      
    if self.cmd.update:
      self.sync_safir()
      return    
    
    #Start a thread that handles the event when minion has finished the test case
    event_handler=EventHandler(len(self.minions))
    event_handler.start()
    
    self.upload_test()    
    self.run_test()    
      
    print("Wait for finished signal from the minions")
    event_handler.join()

    #If we received a test finished event then collect the result
    self.collect_result()

def main():
  print("===== Start =====")  
  ex=Executor()
  ex.run()
  print("--- Finished! ---")
  return 0  
  
#------------------------------------------------
# If this is the main module, start the program
#------------------------------------------------
if __name__ == "__main__":
  sys.exit(main())
  
