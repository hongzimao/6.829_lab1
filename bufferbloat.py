#!/usr/bin/python

"""6.829 Fall 2016 Mininet Assignment: Bufferbloat
Taken (with permission) from CS244 Spring 2013
"""

from mininet.topo import Topo
from mininet.node import CPULimitedHost
from mininet.link import Link, TCLink, TCIntf
from mininet.net import Mininet
from mininet.log import debug, lg, info
from mininet.util import dumpNodeConnections
from mininet.cli import CLI

from subprocess import Popen, PIPE
from time import sleep, time
from multiprocessing import Process
from argparse import ArgumentParser

from monitor import monitor_qlen
import termcolor as T

import sys
import os
import math

import numpy as np


parser = ArgumentParser(description="Bufferbloat tests")
parser.add_argument('--bw-host', '-B',
                    type=float,
                    help="Bandwidth of host links (Mb/s)",
                    default=1000)

parser.add_argument('--bw-net', '-b',
                    type=float,
                    help="Bandwidth of bottleneck (network) link (Mb/s)",
                    required=True)

parser.add_argument('--delay',
                    type=float,
                    help="Link propagation delay (ms)",
                    required=True)

parser.add_argument('--dir', '-d',
                    help="Directory to store outputs",
                    required=True)

parser.add_argument('--time', '-t',
                    help="Duration (sec) to run the experiment",
                    type=int,
                    default=10)

parser.add_argument('--maxq',
                    type=int,
                    help="Max buffer size of network interface in packets",
                    default=100)

# TODO: include more parser parameters to pass pie/nopie argument
# and num_flows argument from run.sh

# Linux uses CUBIC-TCP by default that doesn't have the usual sawtooth
# behaviour.  For those who are curious, invoke this script with
# --cong cubic and see what happens...
# sysctl -a | grep cong should list some interesting parameters.
parser.add_argument('--cong',
                    help="Congestion control algorithm to use",
                    default="reno")

# Expt parameters
args = parser.parse_args()

class BasicIntf(TCIntf):
    """An interface with TSO and GSO disabled."""

    def config(self, **params):
        result = super(BasicIntf, self).config(**params)

        self.cmd('ethtool -K %s tso off gso off' % self)

        return result

class PIEIntf(BasicIntf):
    """An interface that runs the Proportional Integral controller-Enhanced AQM
    Algorithm. See the man page for info about paramaters:
    http://man7.org/linux/man-pages/man8/tc-pie.8.html."""

    def config(self, limit=1000, target="20ms", **params):
        result = super(PIEIntf, self).config(**params)

        cmd = ('%s qdisc add dev %s' + result['parent'] + 'handle 11: pie' +
               ' limit ' + str(limit) + ' target ' + target)
        parent = ' parent 10:1 '

        debug("adding pie w/cmd: %s\n" % cmd)
        tcoutput = self.tc(cmd)
        if tcoutput != '':
            error("*** Error: %s" % tcoutput)
        debug("cmd:", cmd, '\n')
        debug("output:", tcoutput, '\n')
        result['tcoutputs'].append(tcoutput)
        result['parent'] = parent
         
        return result

class AQMLink(Link):
    """A link that runs an AQM scheme on 0-2 of its interfaces."""

    def __init__(self, node1, node2, port1=None, port2=None, intfName1=None,
                 intfName2=None, cls1=TCIntf, cls2=TCIntf, **params):
        super(AQMLink, self).__init__(node1, node2, port1=port1, port2=port2,
                                      intfName1=intfName1, intfName2=intfName2,
                                      cls1=cls1, cls2=cls2, params1=params,
                                      params2=params)

class BBTopo(Topo):
    "Simple topology for bufferbloat experiment."

    def __init__(self, n=2):
        super(BBTopo, self).__init__()

        # TODO: create two hosts

        # Here I have created a switch.  If you change its name, its
        # interface names will change from s0-eth1 to newname-eth1.
        s0 = self.addSwitch('s0')

        # TODO: Add links -- with appropriate characteristics 
        # h1 has fast connection
        # h2 has slow uplink connection
        # Note: use "bw=bw_host" instead of "bw=bw-host"
        # Note: needs to add in cls1=BasicIntf, cls2=BasicIntf when setup the link
        # Hint: PIE inteface sits on the switch side, so which cls you need to change?
	    
        return

# Simple wrappers around monitoring utilities.  You are welcome to
# contribute neatly written (using classes) monitoring scripts for
# Mininet!
def start_tcpprobe(outfile="cwnd.txt"):
    os.system("rmmod tcp_probe; modprobe tcp_probe full=1;")
    Popen("cat /proc/net/tcpprobe > %s" % (outfile),
          shell=True)

def stop_tcpprobe():
    Popen("killall -9 cat", shell=True).wait()

# Queue monitoring
def start_qmon(iface, interval_sec=0.1, outfile="q.txt"):
    monitor = Process(target=monitor_qlen,
                      args=(iface, interval_sec, outfile))
    monitor.start()
    return monitor

def start_iperf(net):
    h2 = net.getNodeByName('h2')
    print "Starting iperf server..."
    # For those who are curious about the -w 16m parameter, it ensures
    # that the TCP flow is not receiver window limited.  If it is,
    # there is a chance that the router buffer may not get filled up.
    server = h2.popen("iperf -s -w 16m")

    # TODO: Start the iperf client on h1.  Ensure that you create a
    # long lived TCP flow.
    # Hint: uses -P 10 in the iperf argument to introduce 10 flows

    # Note that unlike the CLI, where mininet automatically translates
    # nodes names (like h1) to IP addresses, here it's up to you.

def start_webserver(net):
    h2 = net.getNodeByName('h2')
    proc = h2.popen("python http/webserver.py", shell=True)
    sleep(1)
    return [proc]

def start_ping(net, outfile="ping.txt"):
    # TODO: Start a ping train from h1 to h2 (or h2 to h1, does it
    # matter?)  Measure RTTs every 0.1 second.  Read the ping man page
    # to see how to do this.
    #
    # Hint: Use host.popen(cmd, shell=True).  If you pass shell=True
    # to popen, you can redirect cmd's output using shell syntax.
    # i.e. ping ... > /path/to/ping.
    # Hint: Use -i 0.1 in ping to ping every 0.1 sec

def bufferbloat():
    if not os.path.exists(args.dir):
        os.makedirs(args.dir)
    os.system("sysctl -w net.ipv4.tcp_congestion_control=%s" % args.cong)
    topo = BBTopo()
    net = Mininet(topo=topo, host=CPULimitedHost, link=AQMLink)
    net.start()
    
    # Hint: The command below invokes a CLI which you can use to
    # debug.  It allows you to run arbitrary commands inside your
    # emulated hosts h1 and h2.
    # Note: It can take a while to pop out xterm windows in GCP.
    # CLI(net)
    
    # This dumps the topology and how nodes are interconnected through
    # links.
    dumpNodeConnections(net.hosts)
    
    # This performs a basic all pairs ping test.
    net.pingAll()

    # Start all the monitoring processes
    start_tcpprobe("%s/cwnd.txt" % (args.dir))

    # TODO: Start monitoring the queue sizes.  Since the switch I
    # created is "s0", I monitor one of the interfaces.  Which
    # interface?  The interface numbering starts with 1 and increases.
    # Depending on the order you add links to your network, this
    # number may be 1 or 2.  Ensure you use the correct number.

    # TODO: Start iperf, webservers, ping.

    # TODO: measure the time it takes to complete webpage transfer
    # from h1 to h2 (say) 3 times.  Hint: check what the following
    # command does: curl -o /dev/null -s -w %{time_total} google.com
    # Now use the curl command to fetch webpage from the webserver you
    # spawned on host h1 (not from google!)
    # Hint: Where is the webserver located?

    # Hint: have a separate function to do this and you may find the
    # loop below useful.
    start_time = time()
    while True:
        # do the measurement (say) 3 times.

        sleep(5)
        now = time()
        delta = now - start_time

        if delta > args.time:
            break
        print "%.1fs left..." % (args.time - delta)

    # TODO: compute average (and standard deviation) of the fetch
    # times.  You don't need to plot them.  Just note it in your
    # README and explain.

    stop_tcpprobe()
    qmon.terminate()
    net.stop()
    # Ensure that all processes you create within Mininet are killed.
    # Sometimes they require manual killing.
    Popen("pgrep -f webserver.py | xargs kill -9", shell=True).wait()

if __name__ == "__main__":
    bufferbloat()
