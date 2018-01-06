const axios = require('axios');
const state = require('./state');

const api = axios.create({
    baseURL: state.auth.apiRoot,
    timeout: 10000,
    headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Api-Key': state.auth.apiKey
    }
});

module.exports = api;
