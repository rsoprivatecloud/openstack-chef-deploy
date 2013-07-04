nginx["ssl_port"] = 4000
nginx["non_ssl_port"] = 4080
nginx["enable_non_ssl"] = true
rabbitmq["enable"] = false
rabbitmq["password"] = "chuc93prethugucR"
bookshelf['url'] = "https://#{node['ipaddress']}:4000"
