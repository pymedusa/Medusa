const domLoaded = require('dom-loaded');
const Debug = require('debug');
const state = require('./state');
const medusa = require('./medusa');
const routes = require('./routes');

state.components.jumpToTop = '<img src="images/top.gif" width="31" height="11" alt="Jump to top" />';

const debug = new Debug('medusa');

const UTIL = {
    exec(controller, action) {
        action = (action === undefined) ? 'init' : action;

        if (controller !== '' && routes[controller] && typeof routes[controller][action] === 'function') {
            debug(`exec: routes[${controller}][${action}]();`);
            routes[controller][action]();
        } else {
            debug(`couldnt find routes[${controller}][${action}]();`);
        }
    },
    init() {
        const { apiRoot, apiKey } = state.auth;
        $('[asset]').each(function() {
            const asset = $(this).attr('asset');
            const series = $(this).attr('series');
            const path = apiRoot + 'series/' + series + '/asset/' + asset + '?api_key=' + apiKey;
            if (this.tagName.toLowerCase() === 'img') {
                if ($(this).attr('lazy') === 'on') {
                    $(this).attr('data-original', path);
                } else {
                    $(this).attr('src', path);
                }
            }
            if (this.tagName.toLowerCase() === 'a') {
                $(this).attr('href', path);
            }
        });

        const body = document.body;
        const controller = body.getAttribute('data-controller');
        const action = body.getAttribute('data-action');

        UTIL.exec('common');
        UTIL.exec(controller);
        UTIL.exec(controller, action);
    }
};

const bootMedusa = async () => {
    state.config = await medusa.config().catch(err => {
        log.error(err);
        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
    });

    log.setDefaultLevel('trace');
    state.components.themeSpinner = state.config.themeName === 'dark' ? '-dark' : '';
    state.components.loading = '<img src="images/loading16' + state.config.themeSpinner + '.gif" height="16" width="16" />';

    // Call the notificaitons, etc. here
    // triggerConfigLoaded();
    UTIL.init();
};

// Setup Medusa is we're not on the login page.
domLoaded.then(async () => {
    if (!document.location.pathname.endsWith('/login/')) {
        await bootMedusa();
    }
});
