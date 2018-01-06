const Medusa = require('medusa-lib');
const state = require('./state');

const medusa = new Medusa({
    url: state.auth.apiRoot,
    apiKey: state.auth.apiKey
});

module.exports = medusa;
