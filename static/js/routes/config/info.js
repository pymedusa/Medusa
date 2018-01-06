const Vue = require('vue/dist/vue.common');
const state = require('../../state');
const medusa = require('../../');

const info = async () => {
    const app = new Vue({
        el: '#config-content',
        data: await medusa.config(),
        methods: {
            redirect(e) {
                e.preventDefault();
                window.open(state.config.anonRedirect + e.target.href, '_blank');
            },
            prettyPrintJSON(x) {
                return JSON.stringify(x, undefined, 4);
            }
        }
    });
    $('[v-cloak]').removeAttr('v-cloak');

    return app;
};

module.exports = info;
