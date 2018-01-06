const path = require('path');
const state = require('statux');

state.config = {};
state.auth.apiRoot = state.auth.apiRoot || path.join(document.getElementsByTagName('base')[0].href, '/api/v2/');
state.auth.apiKey = state.auth.apiKey || document.getElementsByTagName('body')[0].getAttribute('api-key');
state.components = {
    loading: '',
    themeSpinner: ''
};

window.state = state;
module.exports = state;
