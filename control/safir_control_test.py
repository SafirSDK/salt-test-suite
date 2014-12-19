#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, subprocess, sys, getopt, time
from socket import gethostname

seed_minion = "minion00"
node_count = 20

def ip_address(host_name):
  ip="192.168.66.1"+host_name[len(host_name)-2:]
  return ip

def set_env(name, value):
  if os.environ.get(name) is not None:
    os.environ[name]+=os.pathsep+value
  else:
    os.environ[name]=value
    
def safir_control_cmd():
  my_name=gethostname()
  if my_name==seed_minion:
    return ["safir_control",
            "--control-address", ip_address(my_name)+":33000",
            "--data-address", ip_address(my_name)+":44000"]
  else:
      return ["safir_control",
              "--control-address", ip_address(my_name)+":33000",
              "--data-address", ip_address(my_name)+":44000",
              "--seed", ip_address(seed_minion)+":33000"]
  
def linux_main():
  try:
    f=open("/home/safir/result.txt", "w")
    set_env("HOME", "/home/safir")
    set_env("PATH", "/home/safir/safir/runtime/bin")
    set_env("LD_LIBRARY_PATH", "/home/safir/safir/runtime/lib")
    set_env("SAFIR_RUNTIME", "/home/safir/safir/runtime")
    
    subprocess.call(safir_control_cmd(), stdout=f, stderr=f)
  except getopt.GetoptError as err:
    f.write(err)
  except:
    f.write("Exception caught")
    
  f.flush()
  f.close()

def windows_main():
  try:
    f=open("c:\\Users\\safir\\result.txt", "w")    
    set_env("PATH", "c:\\Users\\safir\\safir\\runtime\\bin")
    set_env("SAFIR_RUNTIME", "c:\\Users\\safir\\safir\\runtime")
    subprocess.call(safir_control_cmd(), stdout=f, stderr=f, shell=True)
  except getopt.GetoptError as err:
    f.write(err)
  except:
    f.write("Exception caught")
    
  f.flush()
  f.close()
  
def main():  
  global node_count
  opts, args = getopt.getopt(sys.argv[1:], "", ["node-count="])
  for o, a in opts:
    if o=="--node-count":
      node_count=int(a)
  
  if sys.platform.lower().startswith('linux'):
    linux_main()
  elif sys.platform.lower().startswith('win'):
    windows_main()

  #signal that we are done
  subprocess.call(["salt-call", "event.fire_master", gethostname(), "control_test"])
   
#------------------------------------------------
# If this is the main module, start the program
#------------------------------------------------
if __name__ == "__main__":
  main()
  
