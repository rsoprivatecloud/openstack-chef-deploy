#!/usr/bin/env bash

set -e
set -x

RPCS_DIR=${RPCS_DIR:-"/opt/rpcs"}
RPCS_REPO_DIR=${RPCS_DIR}/chef-cookbooks
RPCS_COOKBOOK_DIR=${RPCS_REPO_DIR}/cookbooks
RPCS_COOKBOOK_REPO=${RPCS_COOKBOOK_REPO:-"https://github.com/rcbops/chef-cookbooks"}
RPCS_COOKBOOK_BRANCH=${RPCS_COOKBOOK_BRANCH:-"grizzly"}

# Git tag to deploy from. If not set, it will default to the latest stable release.
# Set to "none" to not checkout a tag and deploy from HEAD of RPCS_COOKBOOK_BRANCH.
RPCS_COOKBOOK_TAG=${RPCS_COOKBOOK_TAG:-"v4.1.2"}

RPCS_TMP=$(mktemp -d /tmp/rpcs-XXXXXXX)

get_distro() {
	if [[ -f "/etc/redhat-release" ]]; then
		export DISTRO="rhel"
	elif [[ -f "/etc/debian_version" ]]; then
		export DISTRO="ubuntu"
	else
		echo "Unrecognized distribution. Aborting."
		exit 1
	fi
}

is_rhel() {
	[[ "$DISTRO" == "rhel" ]]
}

maybe_mkdir() {
	[ -d "$1" ] || mkdir -p "$1"
}

install_dependencies() {
	local PACKAGES="rabbitmq-server git curl vim"

	# TODO(dw): This is kinda gross and depends on the erlang cookie being
	#           the default for the rabbitmq cookbook
	local RABBITMQ_DIR="/var/lib/rabbitmq"
	local RABBITMQ_COOKIE_FILE="${RABBITMQ_DIR}/.erlang.cookie"
	local RABBITMQ_COOKIE="AnyAlphaNumericStringWillDo"

	maybe_mkdir $RABBITMQ_DIR
	echo -n $RABBITMQ_COOKIE > $RABBITMQ_COOKIE_FILE
	chmod 0400 $RABBITMQ_COOKIE_FILE


	if is_rhel; then
		rpm -Uvh --replacepkgs "http://download.fedoraproject.org/pub/epel/6/i386/epel-release-6-8.noarch.rpm"
		yum install -y $PACKAGES

		# TODO(dw): Remove if preseeded erlang cookie process changes
		chown -R rabbitmq. $RABBITMQ_DIR
	else
		export DEBIAN_FRONTEND=noninteractive
		apt-get update
		apt-get install -y $PACKAGES
	fi
}

rabbitmq_user() {
	local RABBITMQ_CTL=/usr/sbin/rabbitmqctl
	local USER=${1}
	local PASSWORD=${2}
	local VHOST=${3:-/}

	$RABBITMQ_CTL add_vhost "$VHOST"
	$RABBITMQ_CTL add_user "${USER}" "${PASSWORD}"
	$RABBITMQ_CTL set_permissions -p "${VHOST}" "${USER}" '.*' '.*' '.*'
}

install_chef_server() {
	local OPSCODE_BASE_URL="https://opscode-omnibus-packages.s3.amazonaws.com"
	local CHEF_RMQ_USER=chef
	local CHEF_RMQ_VHOST=/chef
	local CHEF_RMQ_PW=$(tr -dc a-zA-Z0-9 < /dev/urandom | head -c 24)
	local CHEF_SERVER_DEB="${OPSCODE_BASE_URL}/ubuntu/12.04/x86_64/chef-server_11.0.8-1.ubuntu.12.04_amd64.deb"
	local CHEF_SERVER_RPM="${OPSCODE_BASE_URL}/el/6/x86_64/chef-server-11.0.8-1.el6.x86_64.rpm"


	if is_rhel; then
		service rabbitmq-server start
		rpm -Uvh $CHEF_SERVER_RPM
	else
		local TMP_DEB="${RPCS_TMP}/chef_server.deb"
		wget -O "$TMP_DEB" $CHEF_SERVER_DEB
		dpkg -i "$TMP_DEB"
	fi

	rabbitmq_user "$CHEF_RMQ_USER" "$CHEF_RMQ_PW" $CHEF_RMQ_VHOST

	maybe_mkdir /etc/chef-server
	cat > /etc/chef-server/chef-server.rb <<-EOF
	nginx["ssl_port"] = 4000
	nginx["non_ssl_port"] = 4080
	nginx["enable_non_ssl"] = true
	rabbitmq["enable"] = false
	rabbitmq["password"] = "$CHEF_RMQ_PW"
	bookshelf['url'] = "https://#{node['ipaddress']}:4000"
	EOF

	chef-server-ctl reconfigure
}

configure_knife() {
	local CHEF_INSTALL_SCRIPT="http://opscode.com/chef/install.sh"

	bash <(wget -O - $CHEF_INSTALL_SCRIPT)

	local CHEF_SERVER_URL=https://$(ohai ipaddress | awk '/^ / {gsub(/ *\"/, ""); print; exit}'):4000

	maybe_mkdir /root/.chef

	cat > /root/.chef/knife.rb <<-EOF
	log_level                :info
	log_location             STDOUT
	node_name                'admin'
	client_key               '/etc/chef-server/admin.pem'
	validation_client_name   'chef-validator'
	validation_key           '/etc/chef-server/chef-validator.pem'
	chef_server_url          '$CHEF_SERVER_URL'
	cache_options( :path => '/root/.chef/checksums' )
	cookbook_path            [ '${RPCS_COOKBOOK_DIR}' ]
	EOF
}

upload_cookbooks() {
	maybe_mkdir $RPCS_DIR

	git clone --recursive -b $RPCS_COOKBOOK_BRANCH $RPCS_COOKBOOK_REPO $RPCS_REPO_DIR
	
	if [[ "$RPCS_COOKBOOK_TAG" != "none" ]]; then
		cd $RPCS_REPO_DIR
		git checkout $RPCS_COOKBOOK_TAG
		git submodule update
		cd -
	fi

	add_opscode_cookbook "cron" "1.2.6"
	add_opscode_cookbook "chef-client" "3.0.6"

	knife cookbook upload -a
	knife role from file ${RPCS_REPO_DIR}/roles/*.rb
}

add_opscode_cookbook() {
	local COOKBOOK_TARBALL="${RPCS_TMP}/${1}.tar.gz"
	knife cookbook site download -f "$COOKBOOK_TARBALL" "$1" "$2"
	tar xf "$COOKBOOK_TARBALL" -C $RPCS_COOKBOOK_DIR
}

create_environment() {
	if [[ -n "$1" && -r "$1" ]]; then
		knife environment from file "$1"
	fi
}

run_parts() {
	if [[ -n "$1" && -d "$1" ]]; then
		run-parts -v "$1"
	fi
}

run_spiceweasel() {
	local CHEF_BIN_DIR="/opt/chef/embedded/bin"
	local CHEF_GEM="${CHEF_BIN_DIR}/gem"

	run_parts pre-bootstrap.d

	if [[ -n "$1" && -r "$1" ]]; then
		if is_rhel; then
			yum install -y make gcc libxml2-devel libxslt-devel 
		else
			apt-get install -y make gcc libxml2-dev libxslt1-dev
		fi

		# Chef and spiceweasel agree on json 1.7.7 as a dependency
		${CHEF_GEM} uninstall -I json
		${CHEF_GEM} install --no-ri --no-rdoc json --version 1.7.7
		${CHEF_GEM} install --no-ri --no-rdoc spiceweasel
		${CHEF_BIN_DIR}/spiceweasel -e --novalidation -T 3600 "$1"
	fi

	run_parts post-bootstrap.d
}

cleanup() {
	if [[ -d "${RPCS_TMP}" ]]; then
		rm -rf "${RPCS_TMP}"
	fi
}

trap cleanup EXIT

get_distro
install_dependencies
install_chef_server
configure_knife
upload_cookbooks
create_environment "$1"
run_spiceweasel "$2"

# vim: ts=4 sw=4 noexpandtab
