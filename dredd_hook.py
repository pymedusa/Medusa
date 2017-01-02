import ConfigParser
import dredd_hooks as hooks

web_username = 'test_username'
web_password = 'test_password'
api_key = 'test_api_key'

@hooks.before_all
def set_auth(transaction):
    config = ConfigParser.RawConfigParser()
    config.read(r'config.ini')
    config.set('General', 'web_username', web_username)
    config.set('General', 'web_password', web_password)
    config.set('General', 'api_key', api_key)
    with open('config.ini', 'wb') as configfile:
        config.write(configfile)

@hooks.before_each
def add_api_key(transaction):
    transaction['request']['headers']['x-api-key'] = api_key

@hooks.before('/authenticate > POST')
def add_auth(transaction):
    del transaction['request']['headers']['x-api-key']
    transaction['request']['body']['username'] = web_username
    transaction['request']['body']['password'] = web_password
