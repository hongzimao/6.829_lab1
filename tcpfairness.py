#!/usr/bin/env python
"""
Created on September 1, 2016

@author: aousterh
"""

from subprocess import check_output, STDOUT

from mininet.cli import CLI
from mininet.node import Host, Node
from mininet.link import Intf, Link, TCIntf
from mininet.log import debug, error, setLogLevel
from mininet.net import Mininet
from mininet.nodelib import LinuxBridge
from mininet.topo import Topo

class CustomMininet(Mininet):
    """A Mininet with some custom features."""

    def addSwitch(self, name, cls=None, **params):
        sw = super(CustomMininet, self).addSwitch(name, cls, **params)

        if sw.inNamespace:
            # add a loopback interface so that we can use xterm with switches
            # in their own namespaces
            sw.cmd('ifconfig lo up')

        return sw

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
        parent = ' parent 11:1 '

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

class TwoSwitchTopo(Topo):
    """Topology with two switches. Switch 1 has 3 hosts, switch 2 has 2 hosts,
    switches are connected with a single link."""

    def __init__(self, bw_mbps=100, delay="10ms", max_queue_size=1000,
                 **kwargs):
        super(TwoSwitchTopo, self).__init__(**kwargs)

        link_params = {"bw": bw_mbps, "delay": delay,
                       "max_queue_size": max_queue_size}


        s1 = self.addSwitch('s1', inNamespace=True)
        s2 = self.addSwitch('s2', inNamespace=True)

        # TODO: create hosts and add appropriate links between hosts and switches

        # TODO: create link between switches, notice that the delay is different
	
	# Hint: you can use **link_params to pass parameters when creating links
	# Hint: remember to enable PIE for these links: for links between hosts and
	# switches, mimic bufferbloat.py, PIE should sit on the switch side; for the
	# link between switches, enable PIE on both sides.

def set_congestion_control(cc="reno"):
    res = check_output(["sysctl", "-w",
                        "net.ipv4.tcp_congestion_control=" + cc],
                       stderr=STDOUT)
    if res != ("net.ipv4.tcp_congestion_control = %s\n" % cc):
        print "Error setting congestion control to %s. Exiting." % cc
        exit()

def main():
    set_congestion_control("reno")

    setLogLevel('info') # set to 'debug' for more logging

    topo = TwoSwitchTopo()
    net = CustomMininet(topo=topo, switch=LinuxBridge, controller=None,
                        xterms=True, link=AQMLink)
    net.start()

    # First, use CLI to explore this setting, i.e. run iperf on multiple hosts and run ping
    # Note: It can take a while to pop out xterm windows in GCP.
    CLI(net)
    
    # TODO: Then, comment out CLI(net) and mimic bufferbloat.py, automate what you did in CLI, 
    # such that running tcpfairness.py will output all the delivers in the problem.
    # Note: Turn off the xterm in CustomMininet by setting xterms=False
    # Let each experiment run for 200 seconds at least
    # When starting off another experiment, remember to initialize net again by doing net = ...

    # Hint: "iperf -c ... -P 10 | grep SUM" gives aggregation information of 10 flows
    # "iperf -c -i 1 ..." gives a measurement every 1 second
    # Instead of tcpprobe, you can use "iperf -c ... > txtfile" to store the results.
    # 

    net.stop()

if __name__ == '__main__':
    main()
