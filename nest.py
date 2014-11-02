#! /usr/bin/python
# -*- coding: utf-8 -*-

import urllib
import urllib2
import sys
import json
from optparse import OptionParser

class Nest:
  def __init__(self, username, password, serial=None, index=0, units="F"):
    self.username = username
    self.password = password
    self.serial   = serial
    self.units    = units
    self.index    = index

  def login(self):
    data = urllib.urlencode({"username": self.username, "password": self.password})
    req  = urllib2.Request("https://home.nest.com/user/login", data, {"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4"})
    res  = urllib2.urlopen(req).read()
    res  = json.loads(res)

    self.transport_url = res["urls"]["transport_url"]
    self.access_token  = res["access_token"]
    self.userid        = res["userid"]

  def update(self):
    req = urllib2.Request(self.transport_url + "/v2/mobile/user." + self.userid,
                          headers={"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4",
                                   "Authorization":"Basic " + self.access_token,
                                   "X-nl-user-id": self.userid,
                                   "X-nl-protocol-version": "1"})
    res = urllib2.urlopen(req).read()
    res = json.loads(res)
    self.structure_id = res["structure"].keys()[0]

    if not self.serial:
      self.device_id = res["structure"][self.structure_id]["devices"][self.index]
      self.serial = self.device_id.split(".")[1]

    self.status = res

  def show_status(self):
    shared = self.status["shared"][self.serial]
    device = self.status["device"][self.serial]

    allvars = shared
    allvars.update(device)

    for k in sorted(allvars.keys()):
      print k + "."*(32-len(k)) + ":", allvars[k]

  def get_temp(self):
    return self.status["shared"][self.serial]["current_temperature"]

  def get_humidity(self):
    return self.status["device"][self.serial]["current_humidity"]

  def set_temperature(self, temp):
    data = '{"target_change_pending":true,"target_temperature":' + '%0.1f' % temp + '}'
    req = urllib2.Request(self.transport_url + "/v2/put/shared." + self.serial,
                          data,
                          {"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4",
                           "Authorization":"Basic " + self.access_token,
                           "X-nl-protocol-version": "1"})
    res = urllib2.urlopen(req).read()
    return res

  def set_fan(self, state):
    data = '{"fan_mode":"' + str(state) + '"}'
    req = urllib2.Request(self.transport_url + "/v2/put/device." + self.serial,
                          data,
                          {"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4",
                           "Authorization":"Basic " + self.access_token,
                           "X-nl-protocol-version": "1"})

    res = urllib2.urlopen(req).read()
    return res

if __name__ == "__main__":
  parser = OptionParser()
  parser.add_option("-u", "--user", help="username for nest.com")
  parser.add_option("-p", "--password", help="password for nest.com")
  parser.add_option("-s", "--serial", default=None, help="optional, specify serial number of nest thermostat to talk to") 
  parser.add_option("-i", "--index", default=0, type="int", help="optional, specify index number of nest to talk to")
  parser.add_option("-x", "--humidity", action="store_true", help="print the humidity")
  parser.add_option("-t", "--temperature", action="store_true", help="print the temperature")
  parser.add_option("-f", "--fahrenheit", action="store_true", help="temp should be in fahrenheit (default is celsius)")
  parser.add_option("-a", "--all", action="store_true", help="print both temp and humidity")
  opts, args = parser.parse_args()

  if not opts.user or not opts.password:
    print "Username and password are required"
    sys.exit(-1)

  n = Nest(opts.user, opts.password, opts.serial, opts.index)
  n.login()
  n.update()

  if opts.all:
    t = n.get_temp()
    suffix = "C"
    if opts.fahrenheit:
      t = 9*t/5 + 32
      suffix = "F"
    print "%0.1f° %s" % (t, suffix),
    print "@ %d%% humidity" % n.get_humidity()
  else:
    if opts.temperature:
      t = n.get_temp()
      suffix = "C"
      if opts.fahrenheit:
        t = 9*t/5 + 32
        suffix = "F"
      print "%0.1f° %s" % (t, suffix)

    if opts.humidity:
      print "%d%% humidity" % n.get_humidity()
