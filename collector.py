#!/usr/bin/env python

#collector.py
#a quick hack to generate json output from rrd data files generated by collectd
#
#Copyright 2014 Manuel Munz <freifunk at somakoma dot de>
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0

__author__="soma"
__date__ ="$10.04.2014 20:15:00$"
__version__="0.0.3"


import os
import json
import subprocess
import glob
from rrdtool import update as rrd_update
try:
    from collections import OrderedDict as odict
except ImportError:
    from ordereddict import OrderedDict as odict
    
from config import *

def getHosts():
    for filename in os.listdir(path):
        hosts.append(filename)


def createRRD(key, source, datasources):
    RRD = ''
    #hosts = ['bg23wozi']
    if not source:
        # no source given - find all datasources for the given key
        if key == 'interface':
            # is it old or new format?
            for host in hosts:
                plugindir = os.path.join(path, host, key)
                
                if os.path.exists(plugindir):
                    # old format: <host>/interface/if_octets-<instance>.rrd
                    instancesraw = glob.glob(plugindir + '/if_octets-*')
                    instances = []
                    format = 'old'
                    for instance in instancesraw:
                        instance = instance.replace(plugindir + '/if_octets-', '')
                        instance = instance.replace('.rrd', '')
                        instances.append(instance)
                else:
                    # it is new format
                    # <host>/interface/<instance>/if_octets.rrd
                    format = 'new'
                    instancesraw = glob.glob(plugindir + '-*')
                    instances = []
                    for instance in instancesraw:
                        instance = instance.replace(plugindir + '-', '')
                        instances.append(instance)            
                
                for instance in instances:
                    if format == 'old':
                        file = plugindir + '/if_octets-' + instance.replace('DOTSNOTALLOWED', '.') + '.rrd'
                    else:
                        file = plugindir + '-' + instance.replace('DOTSNOTALLOWED', '.') + '/if_octets.rrd'
                        
                    if os.path.exists(file):
                        id = host.replace('.', 'DOTSNOTALLOWED') + '_' + instance
                        datasources = ['tx', 'rx']
                        for ds in datasources:
                            instanceid = id + '_' + ds
                            instanceid = instanceid.replace('.', 'DOTSNOTALLOWED')
                            RRD += 'DEF:last_%s_raw=%s:%s:AVERAGE:step=30 ' % (instanceid, file, ds)
                            #RRD += 'VDEF:last_%s=last_%s_raw ' % (instanceid, instanceid)
                            RRD += 'XPORT:last_%s_raw:%s ' % (instanceid, instanceid) 
                    
        
    else:
        for host in hosts:
            file = os.path.join(path, host, source)
            if os.path.exists(file):
                for ds in datasources:
                    id = host.replace('.', 'DOTSNOTALLOWED') + '_' + ds
                    RRD += 'DEF:last_%s_raw=%s:%s:AVERAGE:step=30 ' % (id, file, ds)
                    #RRD += 'CDEF:last_%s=last_%s_raw ' % (id, id)
                    RRD += 'XPORT:last_%s_raw:%s ' % (id, id)
    if debug:
        print(RRD)
    return RRD


def createAggregatedRRDPath():
    aggregatedPath = path + '/aggregated'
    try:
        os.makedirs(aggregatedPath)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
        
def createRRDAggregated(plugin, ds, filename):
    interfaceTotals = aggregatedPath + '/' + plugin + '-total' + '/' + filename
    if not os.path.exists(interfaceTotals):
        # todo: well, do something
        pass
        

def updateSummaryRRD():
    for plugin in outSummary:
        file = os.path.join(summaryPath, "summary/" + plugin + "/" + plugin + ".rrd")
	if plugin == "interface":
	    # /var/lib/collectd/rrd-summary/summary/interface-summary/if_octets.rrd
            file = os.path.join(summaryPath, "summary/interface-summary/if_octets.rrd")

        if os.path.exists(file):
            pluginValues = outSummary[plugin]
            values = pluginValues.values()
            updateValues = ':'.join(str(v) for v in values)

            if len(updateValues) > 0:
                try:
                    ret = rrd_update(file, 'N:%s' % updateValues)
                    if ret:
                        print(ret)
                        # print("Updated rrd %s with values: %s" % (plugin, updateValues))
                    if debug: 
                        print("Updated rrd %s with values: %s" % (plugin, updateValues))
                except IOError:
                    print("Could not write to %s" % file)
             

def getJsonRaw(RRD, plugin):
    #flush = '/usr/bin/collectdctl -s /var/run/collectd-unixsock flush plugin=%s' % plugin
    #os.system(flush)
    cmd = rrdtoolBinary + ' xport -s now-600s -e -1 --json \\' + RRD + '\n'
    op = subprocess.Popen([cmd, ""], stdout=subprocess.PIPE, shell=True)
    json, err = op.communicate()
    # rrdtool 1.4.8 still produces invalid json, fix it here
    json = json.replace('about:', '"about":')
    json = json.replace('meta:', '"meta":')
    json = json.replace('\'', '"')
    json = json.replace('DOTSNOTALLOWED', '.')
    if debug:
        print('JSON raw data:')
        print(json)
    return json

def parseData(key, data):
    i = 0
    instance = False
    for h in data['meta']['legend']:
        harr = h.split('_')
        if len(harr) > 2:
            instance = harr[2]
        ds = harr[1]
        h = harr[0]
        if not h in out:
            out[h] = odict()

        meta = data['meta']
        meta.pop('legend', None)
        if not key in out[h]:
            out[h][key] = odict()
        
        out[h][key]['meta'] = meta
        
        if not 'data' in out[h][key]:
            out[h][key]['data'] = odict()
        if not instance:
            if not ds in out[h][key]['data']:
                out[h][key]['data'][ds] = []
        else:
            if not ds in out[h][key]['data']:
                out[h][key]['data'][ds] = odict()
            if not instance in out[h][key]['data'][ds]:
                out[h][key]['data'][ds][instance] = []        
                 
        for j in range(0, len(data['data'])):
            if not instance:
                out[h][key]['data'][ds].insert(0, data['data'][j][i])
            else:
                out[h][key]['data'][ds][instance].insert(0, data['data'][j][i])
        i = i + 1

def getData(key, rra, datasources ):
    RRD = createRRD(key, rra, datasources);
    if RRD:
        data = getJsonRaw(str(RRD), key)
        data = json.loads(data)
        parseData(key, data)
        
def writeFile(filename, content):
    try:
        f = open(outdir + filename, "w")
        try:
            f.write(str(content))
        finally:
            f.close()
    except IOError:
        print("Error, Could not write output to %s" % outdir + filename)

def formatValue(value, plugin):
    if plugin == 'splash_leases' or plugin == 'uptime':
        return int(value)
    if isinstance(value, float):
        return round(value, 2)

def latestData(out):
    for host in out:
        outLatest[host] = odict()
        for plugin in out[host]:
            outLatest[host][plugin] = odict()
            for instance in out[host][plugin]['data']:
                if isinstance(out[host][plugin]['data'][instance], list):
                    #outLatest[host][plugin][instance]
                    for v in out[host][plugin]['data'][instance]:
                        if isinstance(v, (int, float)):
                            outLatest[host][plugin][instance] = formatValue(v, plugin)
                            break
                            
                else:
                    outLatest[host][plugin][instance] = odict()
                    for ds in out[host][plugin]['data'][instance]:
                        
                        for v in out[host][plugin]['data'][instance][ds]:
                            if isinstance(v, (int, float)):
                                outLatest[host][plugin][instance][ds] = formatValue(v, plugin)
                                break

def summary(out, plugins):
    for host in out:
        for plugin in out[host]:
            if plugin in plugins:
                if not plugin in outSummary:
                    outSummary[plugin] = odict() 

                
                for instance in out[host][plugin]:
                    if isinstance(out[host][plugin][instance], dict):
                        for v in out[host][plugin][instance]:
                            if not v in outSummary[plugin]:
                                outSummary[plugin][v] = 0
                            outSummary[plugin][v] = int(outSummary[plugin][v]) + int(out[host][plugin][instance][v])
                    else:
                        if not instance in outSummary[plugin]:
                            outSummary[plugin][instance] = 0
                        if isinstance(out[host][plugin][instance], (int, float)):
                            outSummary[plugin][instance] = outSummary[plugin][instance] + out[host][plugin][instance]

if __name__ == "__main__":
    hosts = []
    out = odict()
    outLatest = odict()
    outSummary = odict()
    
    
    getHosts()
    
    getData('splash_leases', 'splash_leases/splash_leases.rrd', ['leased', 'whitelisted', 'blacklisted'] )
    getData('uptime','uptime/uptime.rrd', ['value'] )
    getData('load','load/load.rrd', ['shortterm', 'midterm', 'longterm'] )
    getData('interface', None, 'if_octets')
    
    latestData(out)
    summary(outLatest, ['splash_leases', 'interface'])
    updateSummaryRRD()
    
    
    outLatestPlusSummary = odict()
    outLatestPlusSummary['data'] = outLatest;
    outLatestPlusSummary['summary'] = outSummary
  
    writeFile('all.json', json.dumps(out, indent = 4))
    writeFile('latest.json', json.dumps(outLatestPlusSummary, indent = 4))
    writeFile('summary.json', json.dumps(outSummary))

    print(outSummary)
