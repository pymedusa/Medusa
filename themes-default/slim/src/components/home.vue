<script>
import { mapState } from 'vuex';
import AppLink from './app-link.vue';

module.exports = {
    name: 'home',
    template: '#home-template',
    components: {
        AppLink
    },
    metaInfo: {
        title: 'Home'
    },
    data() {
        return {
            header: 'Show List'
        };
    },
    computed: {
        ...mapState([
            'config'
        ]),
        layout: {
            get() {
                const { config } = this;
                return config.layout.home;
            },
            set(layout) {
                const { $store } = this;
                const page = 'home';
                $store.dispatch('setLayout', { page, layout });
            }
        }
    },
    mounted() {}
};
</script>
