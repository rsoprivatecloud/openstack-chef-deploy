# Deploying OpenStack with Chef Cookbooks
This project aims to make Chef deployments of OpenStack infrastructures easier through the use of [Berkshelf](http://berkshelf.com) and [Spiceweasel](https://github.com/mattray/spiceweasel).

## Overview

### Berkshelf
[Berkshelf](http://berkshelf.com/) is the [Bundler](http://gembundler.com/) equivalent for Chef cookbooks. Just as Bundler has a `Gemfile`, Berkshelf allows us to manage cookbook dependencies for a project in a `Berkfile`, which can easily be uploaded to Chef Server.

### Spiceweasel
TODO(dw)

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
$ berk upload
```

### Spiceweasel
TODO(dw)
