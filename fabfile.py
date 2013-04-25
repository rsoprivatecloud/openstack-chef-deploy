#!/usr/bin/env python

import os
import time

from fabric.api import env, run, put, cd, prompt, sudo, roles
from fabric.colors import red, yellow, green
from fabric.contrib import files
from fabric.exceptions import CommandTimeout
from fabric.utils import puts

# needed to pick up ProxyCommand from config
env.use_ssh_config = True

def install_kvm():
    "Installs KVM/Libvirt"
    puts(green('Installing KVM'))
    sudo('apt-get -qq update')
    sudo('apt-get install -yq qemu-kvm libvirt-bin python-libvirt curl')
    
def create_chef_server(url='http://c390813.r13.cf1.rackcdn.com/chef-server.qcow2',
                       xml_definition='files/chef-server.xml',
                       mgmt_network='10.240.0.0/24'):
    "Creates and configures Chef Server on the controller node"
    assert os.path.exists(xml_definition), 'Chef Server XML definition not found at %s' % xml_definition

    install_kvm()
    sudo('echo iptables-persistent iptables-persistent/autosave_v6 boolean true | debconf-set-selections')
    sudo('echo iptables-persistent iptables-persistent/autosave_v4 boolean true | debconf-set-selections')
    sudo('apt-get install -yq iptables-persistent')

    puts(green('Downloading Chef Server image from %s' % url))
    sudo('mkdir /opt/rpcs', warn_only=True)
    sudo('wget -qO /opt/rpcs/chef-server.qcow2 %s' % url)
    sudo('cp -a /opt/rpcs/chef-server.qcow2{,.pristine}')
    
    puts(green('Configuring Chef Server'))
    sudo('virsh net-autostart default --disable && virsh net-destroy default && virsh net-undefine default', warn_only=True)
    files.uncomment('/etc/sysctl.conf', r'net\.ipv4\.ip_forward=1', use_sudo=True)
    sudo('sysctl net.ipv4.ip_forward=1')

    put(xml_definition, '/opt/rpcs/chef-server.xml', use_sudo=True)
    files.append('/etc/network/interfaces', """
        auto chefbr0
        iface chefbr0 inet static
            address 169.254.123.1
            netmask 255.255.255.0
            bridge_ports none
            bridge_fd 0
            bridge_stp off
            bridge_maxwait 0
        """, use_sudo=True)

    puts(green('Starting the Chef Server VM'))
    sudo('ifup chefbr0')
    sudo('virsh define /opt/rpcs/chef-server.xml')
    sudo('virsh autostart chef-server && virsh start chef-server')
     
    puts(green('Configuring NAT rules'))
    sudo('iptables -t nat -A PREROUTING -s %s -p tcp --dport 4000 -j DNAT --to-dest 169.254.123.2' % mgmt_network)
    sudo('iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE')
    sudo('service iptables-persistent save')

    puts(green('Copying SSH key to Chef Server VM'))
    if not files.exists('/root/.ssh/id_rsa', use_sudo=True):
        sudo('ssh-keygen -b 2048 -N "" -f /root/.ssh/id_rsa -t rsa -q')
    while 'No route to host' in sudo('ssh-keyscan 169.254.123.2 >> /root/.ssh/known_hosts'):
        sleep_time = 10
        puts(yellow('Unable to connect to Chef Server VM. Retrying in %ss...' % sleep_time))
        time.sleep(sleep_time)
    sudo('ssh-copy-id -i /root/.ssh/id_rsa.pub rack@169.254.123.2')

    puts(green('Creating Chef validation and controller client keys'))
    sudo('mkdir -p /root/.chef', warn_only=True)

    retry = True
    long_ass_ssh_command = 'ssh -i /root/.ssh/id_rsa rack@169.254.123.2 "knife client reregister rack -f .chef/rack.pem; knife client reregister chef-validator -f .chef/validation.pem; sudo cp .chef/validation.pem /usr/share/chef-server-api/public; sudo chmod +r /usr/share/chef-server-api/public/validation.pem; yes | knife client delete controller &> /dev/null; knife environment create -d rpcs &>/dev/null; knife client create controller -d -a" | tail -n+2 > /root/.chef/controller.pem'
    while retry is True:
        sleep_time = 10
        try:
            sudo(long_ass_ssh_command, warn_only=True, timeout=15)
            retry = False
        except CommandTimeout:
            puts(yellow('Timeout connecting to Chef Server. Retrying in %ss...' % sleep_time))
            time.sleep(sleep_time)
 
def configure_knife(chef_server_url='http://169.254.123.2:4000/',
                    knife_template='files/knife.rb.tpl'):
    "Installs Chef and configures Knife"
    assert os.path.exists(knife_template), 'Knife configuration template not found at %s' % knife_template
    
    if not chef_server_url.endswith('/'):
        chef_server_url += '/'
    if not chef_server_url.startswith('http'):
        chef_server_url = 'http://' + chef_server_url

    puts(green('Installing Chef'))
    sudo('bash <(curl -sL http://opscode.com/chef/install.sh)')

    puts(green('Creating knife config'))
    sudo('mkdir -p /root/.chef', warn_only=True)
    files.upload_template(knife_template, '/root/.chef/knife.rb', context=locals(), use_sudo=True)   

    sudo('mkdir -p /etc/chef', warn_only=True)
    sudo('wget -nv %svalidation.pem -O /etc/chef/validation.pem' % chef_server_url)

def upload_cookbooks(url="http://github.com/rcbops/chef-cookbooks",
                     branch="v3.0.1"):
    "Uploads OpenStack Chef cookbooks"
    directory = "/opt/rpcs/chef-cookbooks"

    puts(green("Installing dependencies"))
    sudo('apt-get install -qy git')

    if files.exists(directory):
        sudo('rm -rf %s' % directory)

    puts('Cloning chef-cookbooks repository')
    sudo('git clone -q --recursive --depth 1 -b %s %s %s' % (branch, url, directory))

    puts(green("Uploading cookbooks and roles"))
    sudo('knife cookbook upload -c /root/.chef/knife.rb -a')
    sudo('knife role from file /opt/rpcs/chef-cookbooks/roles/*.rb -c /root/.chef/knife.rb')
