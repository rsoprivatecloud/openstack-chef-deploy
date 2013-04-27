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
 
def configure_knife():
    "Installs Chef and configures Knife"

    puts(green('Installing Chef'))
    sudo('bash <(wget -O - http://opscode.com/chef/install.sh)')

    puts(green('Configuring knife'))
    sudo('md5sum /etc/chef-server/admin.pem | knife configure -i -y --defaults '
         '-u controller -s https://localhost:444'
         '--admin-client-key /etc/chef-server/admin.pem '
         '--validation-key /etc/chef-server/chef-validator.pem '
         '-r /opt/rpcs/chef-cookbooks/cookbooks')

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
