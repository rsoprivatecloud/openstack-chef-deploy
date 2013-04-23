# Deploying OpenStack with Chef Cookbooks
This project aims to make Chef deployments of OpenStack infrastructures easier through the use of [fabric](http://fabfile.org) and [Spiceweasel](https://github.com/mattray/spiceweasel).

## Overview

### Fabric
Some stuff about fabric

### Spiceweasel
[Spiceweasel](https:////github.com/mattray/spiceweasel) is a command-line tool for bootstrapping Chef infrastructures. Rather than run individual commands with knife, Spiceweasel allows you to define a template in YAML or JSON for your infrastructure, which it then converts to the appropriate knife commands.

## Getting Started

### Fabric
#### Install fabric


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
