<script>
Vue.use(window['vue-js-toggle-button'].default);
Vue.component('medusa-toggle', {
    extends: window['vue-js-toggle-button'].default,
    template: '<toggle-button></toggle-button>',
    props: {
        height: {
            default: 45,
            type: Number
        },
        width: {
            default: 22,
            type: Number
        },
        id: {
            type: String
        },
        name: {
            type: String
        },
        'v-model': {
            type: String
        },
        sync: {
            default: true,
            type: Boolean
        }
    }
});
</script>
