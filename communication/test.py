#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, subprocess, sys, getopt, time, traceback, random
from socket import gethostname

server_minion = "minion13"
#node_type = "nt1" #nt0 has no multicast, nt1 and nt2 is multicast enabled
node_count = 20
message_count = 1000000 #number of messages to send from server to clients
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
            "-t", "nt1",
            "-w", str(node_count-1),
            "--nsend", str(message_count),
            "--nrecv", "0",
            "--size", str(message_size),
            "--thread-count", "2"]
  else:
    return ["communication_test",
            "-a", ip_address(my_name)+":10000",
            "-s", ip_address(server_minion)+":10000",
            "-t", random.choice(("nt0","nt1","nt2")),
            "-w", str(node_count-1),
            "--nsend", "0",
            "--nrecv", str(message_count),
            "--size", str(message_size),
            "--thread-count", "2"]


def main():
  global node_count
  opts, args = getopt.getopt(sys.argv[1:], "", ["node-count="])
  for o, a in opts:
    if o=="--node-count":
      node_count=int(a)

  ret = 1
  try:
    ret = subprocess.call(communication_test_cmd(),
                          shell = sys.platform == "win32")
  except getopt.GetoptError as err:
    print(err)
  except:
    print("Exception:", traceback.print_exc())

  return ret

#------------------------------------------------
# If this is the main module, start the program
#------------------------------------------------
if __name__ == "__main__":
  sys.exit(main())
