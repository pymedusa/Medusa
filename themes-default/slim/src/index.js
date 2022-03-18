/* eslint-disable import/no-unassigned-import */
import $ from 'jquery';
import 'bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'vue-snotify/styles/material.css';
import '../vendor/js/tablesorter';
import '../vendor/css/open-sans.css';
/* eslint-enable import/no-unassigned-import */

import globalVueShim from './global-vue-shim';

if (window) {
    // @TODO: Remove this before v1.0.0
    window.globalVueShim = globalVueShim;

    // Adding libs to window so mako files can use them
    window.$ = $;
    window.jQuery = $;

    window.MEDUSA = {
        common: {},
        config: {
            general: {},
            layout: {}
        },
        home: {},
        addShows: {}
    };
}

const UTIL = {
    init() {
        $('[v-cloak]').removeAttr('v-cloak');
        window.dispatchEvent(new Event('medusa-loaded'));
    }
};

const { pathname } = window.location;
if (!pathname.includes('/login') && !pathname.includes('/apibuilder')) {
    const configLoaded = event => {
        const { general, layout } = event.detail;

        MEDUSA.config.general = {
            ...MEDUSA.config.general,
            ...general
        };

        const themeSpinner = layout.themeName === 'dark' ? '-dark' : '';
        MEDUSA.config.layout = {
            ...MEDUSA.config.layout,
            ...layout,
            themeSpinner,
            loading: '<img src="images/loading16' + themeSpinner + '.gif" height="16" width="16" />'
        };

        $(document).ready(UTIL.init);
    };
    window.addEventListener('medusa-config-loaded', configLoaded, { once: true });
}
