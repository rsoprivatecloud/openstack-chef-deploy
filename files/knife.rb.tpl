log_level                :info
log_location             STDOUT
node_name                'controller'
client_key               '/root/.chef/controller.pem'
validation_client_name   'chef-validator'
validation_key           '/etc/chef/validation.pem'
chef_server_url          '%(chef_server_url)s'
cache_type               'BasicFile'
cache_options( :path => '/root/.chef/checksums' )
cookbook_path            '/opt/rpcs/chef-cookbooks/cookbooks'
