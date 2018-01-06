const addShows = require('./add-shows');
const common = require('./common');
const config = require('./config');
const errorlogs = require('./errorlogs');
const history = require('./history');
const home = require('./home');
const manage = require('./manage');
const schedule = require('./schedule');

const routes = {
    addShows,
    common,
    config,
    errorlogs,
    history,
    home,
    manage,
    schedule
};

module.exports = routes;
