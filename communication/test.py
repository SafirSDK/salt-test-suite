#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, subprocess, sys, getopt, time, traceback
from socket import gethostname

server_minion = "minion00"
node_type = "nt1" #nt0 has no multicast, nt1 and nt2 is multicast enabled
node_count = 20
message_count = 10000 #number of messages to send from server to clients
message_size = 1400 #message size in bytes

def ip_address(host_name):
  ip="192.168.66.1"+host_name[len(host_name)-2:]
  return ip

def set_env(name, value):
  if os.environ.get(name) is not None:
    os.environ[name]+=os.pathsep+value
  else:
    os.environ[name]=value
    
def communication_test_cmd():
  my_name=gethostname()
  if my_name==server_minion:
    return ["communication_test",
            "-a", ip_address(my_name)+":10000",
            "-t", node_type,
            "-w", str(node_count-1),
            "--nsend", str(message_count),
            "--nrecv", "0",
            "--size", str(message_size),
            "--thread-count", "2"]
  else:
    return ["communication_test",
            "-a", ip_address(my_name)+":10000",
            "-s", ip_address(server_minion)+":10000",
            "-t", node_type,
            "-w", str(node_count-1),
            "--nsend", "0",
            "--nrecv", str(message_count),
            "--size", str(message_size),
            "--thread-count", "2"]
  
def linux_main():
  try:
    f=open("/home/safir/result.txt", "w")
    #set_env("HOME", "/home/safir")
    #set_env("PATH", "/home/safir/safir/runtime/bin")
    #set_env("LD_LIBRARY_PATH", "/home/safir/safir/runtime/lib")
    #set_env("SAFIR_RUNTIME", "/home/safir/safir/runtime")
    
    #subprocess.call(["dots_configuration_check", "-s"], stdout=f, stderr=f)
    #subprocess.call(["communication_test", "-h"], stdout=f, stderr=f)
    subprocess.call(communication_test_cmd(), stdout=f, stderr=f)    
  except getopt.GetoptError as err:
    f.write(err)
  except:
    f.write("Exception: "+traceback.print_exc())
    
  f.flush()
  f.close()

def windows_main():
  try:
    f=open("c:\\Users\\safir\\result.txt", "w")
    set_env("PATH", r"c:\Program Files\Safir SDK Core\bin")
    subprocess.call(communication_test_cmd(), stdout=f, stderr=f, shell=True)
  except getopt.GetoptError as err:
    f.write(err)
  except:
    f.write("Exception: "+traceback.print_exc())
    
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
  subprocess.call(["salt-call", "event.fire_master", gethostname(), "safir_test"])
   
#------------------------------------------------
# If this is the main module, start the program
#------------------------------------------------
if __name__ == "__main__":
  main()
  
