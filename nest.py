#! /usr/bin/python
# -*- coding: utf-8 -*-

import ssl
from functools import wraps

def sslwrap(func):
    @wraps(func)
    def bar(*args, **kw):
      kw['ssl_version'] = ssl.PROTOCOL_TLSv1
      return func(*args, **kw)
    return bar

ssl.wrap_socket = sslwrap(ssl.wrap_socket)

import requests
import sys
import json
import getpass
import datetime
from argparse import ArgumentParser

class Nest:
  def __init__(self, username, password, serial=None, index=0, units="F"):
    self.username = username
    self.password = password
    self.serial   = serial
    self.units    = units
    self.index    = index

    self.user_agent = "Nest/2.1.3 CFNetwork/548.0.4"

  def login(self):
    req  = requests.post("https://home.nest.com/user/login",
                         data={"username": self.username, "password": self.password},
                         headers={"user-agent": self.user_agent})
    res  = req.json()
    req.raise_for_status()

    self.transport_url = res["urls"]["transport_url"]
    self.access_token  = res["access_token"]
    self.userid        = res["userid"]

  def update(self):
    req = requests.get(self.transport_url + "/v2/mobile/user." + self.userid,
                          headers={"user-agent": self.user_agent,
                                   "Authorization":"Basic " + self.access_token,
                                   "X-nl-user-id": self.userid,
                                   "X-nl-protocol-version": 1})
    req.raise_for_status()
    res = req.json()
    self.structure_id = res["structure"].keys()[0]

    if not self.serial:
      self.device_id = res["structure"][self.structure_id]["devices"][self.index]
      self.serial = self.device_id.split(".")[1]

    self.status = res

  def dump_device_info(self):
    shared = self.status["shared"][self.serial]
    device = self.status["device"][self.serial]

    allvars = shared
    allvars.update(device)

    for k in sorted(allvars.keys()):
      print k + "."*(37-len(k)) + ":", allvars[k]

  def _do_request(self, device_or_shared, data):
    url = self.transport_url + "/v2/put/" + device_or_shared + "." + self.serial
    req = requests.post(url, data=data,
                        headers={"Authorization":"Basic " + self.access_token,
                                 "X-nl-user-id": self.userid,
                                 "X-nl-protocol-version": 1})
    req.raise_for_status()
    return req


  # getters
  def get_temp(self):
    return self.status["shared"][self.serial]["current_temperature"]

  def get_humidity(self):
    return self.status["device"][self.serial]["current_humidity"]

  def get_temperature_type(self):
    return self.status["shared"][self.serial]["target_temperature_type"]

  # setters
  def set_temperature(self, temp):
    data = {}
    data["target_change_pending"] = True
    data["target_temperature"] = temp
    return self._do_request("shared", json.dumps(data))

  def set_temperature_type(self, mode):
    data = {}
    data["target_temperature_type"] = mode
    return self._do_request("shared", json.dumps(data))

  def set_fan(self, state):
    data = {}
    data["fan_mode"] = str(state)
    return self._do_request("device", json.dumps(data))

if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("-u", "--user", help="username for nest.com")
  parser.add_argument("-p", "--password", help="password for nest.com")
  parser.add_argument("-s", "--serial", default=None, help="optional, specify serial number of nest thermostat to talk to") 
  parser.add_argument("-i", "--index", default=0, type=int, help="optional, specify index number of nest to talk to")
  parser.add_argument("-y", "--humidity", action="store_true", help="print the humidity")
  parser.add_argument("-t", "--temperature", action="store", nargs="?", const="show", help="print or set the temperature")
  parser.add_argument("-m", "--mode", action="store", nargs="?", const="show", choices=["heat", "cool", "off", "show"])
  parser.add_argument("-f", "--fahrenheit", action="store_true", help="temps in fahrenheit (default is celsius)")
  parser.add_argument("-a", "--all", action="store_true", help="print both temp and humidity")
  parser.add_argument("-c", "--csv", action="store_true", help="print both temp and humidity in CSV format for easy appending to a log file")
  parser.add_argument("-d", "--dump", action="store_true", help="Dump all device info")
  opts = parser.parse_args()

  _user = opts.user
  _pass = opts.password
  if not _user: _user = raw_input("Username: ")
  if not _pass: _pass = getpass.getpass()

  n = Nest(_user, _pass, opts.serial, opts.index)
  n.login()
  n.update()

  if opts.dump:
    n.dump_device_info()

  else:
    if opts.all:
      t = n.get_temp()
      suffix = "C"
      if opts.fahrenheit:
        t = 9*t/5 + 32
        suffix = "F"
      if opts.csv:
        now = datetime.datetime.now().strftime("%x %X")
        print "%s,%0.1f,%d" % (now, t, n.get_humidity()),
      else:
        print "%0.1f° %s" % (t, suffix),
        print "@ %d%% humidity" % n.get_humidity(),
      
      mode = n.get_temperature_type()
      if mode == "heat": mode = "heating"
      elif mode == "cool": mode = "cooling"
      print "(%s)" % mode

    else:
      if opts.mode:
        if opts.mode == "show":
          print n.get_temperature_type()
        else:
          n.set_temperature_type(opts.mode)

      if opts.temperature:
        if opts.temperature == "show":
          t = n.get_temp()
          suffix = "C"
          if opts.fahrenheit:
            t = 9*t/5 + 32
            suffix = "F"
          print "%0.1f° %s" % (t, suffix)
        else:
          try:
            temp = float(opts.temperature)
            if opts.fahrenheit:
              temp = (temp-32)/1.8
            n.set_temperature(temp)
          except TypeError:
            print "Error: temperature must be a number or \"show\""
            sys.exit(1)

      if opts.humidity:
        print "%d%% humidity" % n.get_humidity()
