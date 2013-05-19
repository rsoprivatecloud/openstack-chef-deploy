#!/usr/bin/env python

import os
import time

from fabric.api import env, put, sudo, cd
from fabric.colors import green
from fabric.contrib import files
from fabric.utils import puts

# needed to pick up ProxyCommand from config
env.use_ssh_config = True


def controller():
    """Helper task for bootstrapping a controller

    1. Installs Chef Server 11
    2. Installs and configures knife
    3. Uploads rcbops/chef-cookbooks and roles

    """
    install_chef_server()
    configure_knife()
    upload_cookbooks()
    install_packages()
    #TODO(ramsey): Edit sudoers with NOPASSWD for rack user
    #TODO(ramsey): Generate SSH key for root. Store in a variable for use in other places (i.e. compute nodes)?
    #TODO(ramsey): Disable IPv6
    #TODO(ramsey): Generate MOTD
    #TODO(ramsey): Add all the things to bachrc (i.e. export EDITOR=vim, source /root/.novarc)

def install_chef_server(chef_server_rb='files/chef-server.rb'):
    """Installs Chef Server 11

    Args:
        chef_server_rb: Local path to Chef Server config file

    """
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
 
def configure_knife(chef_server_url="https://localhost:4000"):
    """Installs Chef and configures Knife

    Args:
        chef_server_url: Chef Server URL for knife.rb template

    """
    knife_template = 'files/knife.rb.j2'
    assert os.path.exists(knife_template), \
        'Knife configuration template not found at %s' % knife_template

    puts(green('Installing Chef'))
    sudo('bash <(wget -O - http://opscode.com/chef/install.sh)')

    puts(green('Configuring knife'))
    sudo('mkdir /root/.chef', warn_only=True)
    files.upload_template(knife_template, '/root/.chef/knife.rb',
                          context=locals(), use_sudo=True)

def install_packages(packages=["git","curl","dsh","vim"]):
    """Installs packages from apt repo

    Args:
        packages: Package name that will be installed

    """
    puts(green('Installing %s' % " ".join(packages)))
    sudo('apt-get -qq update')
    sudo('apt-get install -qy %s' % " ".join(packages))


def upload_cookbooks(url="http://github.com/rcbops/chef-cookbooks",
                     branch="v3.0.1",
                     directory="/opt/rpcs/chef-cookbooks"):
    """Uploads Chef cookbooks from a git repository

    Args:
        url: URL for Git repository
        branch: Branch of Git repo to use
        directory: Path to clone repository into

    """

    # We might want to be more careful here
    if files.exists(directory):
        sudo('rm -rf %s' % directory)

    puts('Cloning chef-cookbooks repository')
    sudo('git clone -q --recursive --depth 1 -b %s %s %s'
         % (branch, url, directory))

    puts(green("Uploading cookbooks"))
    sudo('knife cookbook upload -c /root/.chef/knife.rb -a')

    if files.exists('%s/roles' % directory):
        puts(green("Creating roles"))
        sudo('knife role from file %s/roles/*.rb -c /root/.chef/knife.rb'
             % directory)

def bootstrap(spiceweasel_yml):
    """Bootstrap environment based on a Spiceweasel template

    Args:
        spiceweasel_yml: Local path to the Spiceweasel infrastructure template.

    """

    # TODO(dw): If the user does not provide a Spiceweasel template,
    #           generate one by querying using an API Extension, ID,
    #           and filter

    if os.path.exists(spiceweasel_yml):
        tmpfile = '/tmp/spiceweasel.yml'

        # Use the ruby binaries embedded with Chef. This might not be smart.
        with cd('/opt/chef/embedded/bin'):
            puts(green('Installing Spiceweasel'))
            sudo('./gem install spiceweasel --no-ri --no-rdoc')

            puts(green('Uploading Spiceweasel template %s' % spiceweasel_yml))
            put(spiceweasel_yml, tmpfile)

            # TODO(dw): Incomplete. This will pipe into bash when working
            puts(green('Running Spiceweasel'))
            sudo('./spiceweasel -c /root/.chef/knife.rb %s' % tmpfile)

        run('rm -f %s' % tmpfile)
