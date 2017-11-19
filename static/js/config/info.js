const Vue = require('vue/dist/vue.common');
const MEDUSA = require('../core');
const medusa = require('..');

MEDUSA.config.info = async () => {
    const app = new Vue({
        el: '#config-content',
        data: await medusa.config(),
        methods: {
            redirect(e) {
                e.preventDefault();
                window.open(MEDUSA.info.anonRedirect + e.target.href, '_blank');
            },
            prettyPrintJSON(x) {
                return JSON.stringify(x, undefined, 4);
            }
        }
    });
    $('[v-cloak]').removeAttr('v-cloak');

    return app;
};
