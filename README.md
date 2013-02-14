# Deploying OpenStack with Chef Cookbooks
This project aims to make Chef deployments of OpenStack infrastructures easier through the use of [Berkshelf](http://berkshelf.com) and [Spiceweasel](https://github.com/mattray/spiceweasel).

## Overview

### Berkshelf
[Berkshelf](http://berkshelf.com/) is the [Bundler](http://gembundler.com/) equivalent for Chef cookbooks. Just as Bundler has a `Gemfile`, Berkshelf allows us to manage cookbook dependencies for a project in a `Berkfile`, which can easily be uploaded to Chef Server.

### Spiceweasel
[Spiceweasel](https:////github.com/mattray/spiceweasel) is a command-line tool for bootstrapping Chef infrastructures. Rather than run individual commands with knife, Spiceweasel allows you to define a template in YAML or JSON for your infrastructure, which it then converts to the appropriate knife commands.

## Getting Started
This document assumes that you already have Chef Server installed and a registered client with Admin access. These commands are intended to be run as a user with appropriate privileges and valid configurations in their `knife.rb` file. For more information, check out the Opscode Chef documentation.

Before anything else, you should clone this repository and `cd` into the created directory. After that, you're ready to proceed with the Berkshelf and Spiceweasel configurations.

``` bash
$ git clone https://github.com/DavidWittman/openstack-chef-deploy
$ cd openstack-chef-deploy
```

### Uploading cookbooks with Berkshelf
#### Install Berkshelf
``` bash
$ gem install berkshelf
```

#### Upload cookbooks to Chef
``` bash
$ berks upload
```

### Spiceweasel
#### Install Spiceweasel
``` bash
$ gem install spiceweasel
```

#### Edit the spiceweasel.yml file
Edit the **spiceweasel.yml** file to fit your environment. For most deployments, only the node list will need to be updated. See the [Spiceweasel README](https://github.com/mattray/spiceweasel#nodes) for more information.

#### Modify Chef environment
Modify the Chef environment at **environments/rpcs.yml** to fit the specifics of your deployment.

#### Run Spiceweasel
Now, we're going to run Spiceweasel. This will upload your environments and roles to the Chef Server, as well as bootstrap any nodes which you have defined in the **spiceweasel.yml** file.
``` bash
$ spiceweasel spiceweasel.yml | bash
```
