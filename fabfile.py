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

def install_chef_server(chef_server_rb='files/chef-server.rb'):
    chef_server_deb_url = 'https://opscode-omnibus-packages.s3.amazonaws.com'\
        + '/ubuntu/12.04/x86_64/chef-server_11.0.8-1.ubuntu.12.04_amd64.deb'
    puts(green('Downloading Chef Server 11 package'))
    sudo('wget -qO /tmp/chef_server.deb %s' % chef_server_deb_url)
    sudo('dpkg -i /tmp/chef_server.deb')

    if os.path.exists(chef_server_rb):
        sudo('mkdir /etc/chef-server', warn_only=True)
        put(chef_server_rb, '/etc/chef-server/chef-server.rb', use_sudo=True)

    puts(green('Configuring and starting Chef Server 11'))
    sudo('chef-server-ctl reconfigure')
 
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
