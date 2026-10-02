<script>
import { mapState } from 'vuex';
import { waitFor } from '../utils/core';

export default {
    name: 'backstretch',
    render: h => h(), // Doesn't render anything
    props: {
        slug: String
    },
    computed: {
        ...mapState({
            enabled: state => state.config.layout.fanartBackground,
            opacity: state => state.config.layout.fanartBackgroundOpacity,
            apiKey: state => state.auth.apiKey
        }),
        offset() {
            let offset = '90px';
            if ($('#sub-menu-container').length === 0) {
                offset = '50px';
            }
            if ($(window).width() < 1280) {
                offset = '50px';
            }
            return offset;
        }
    },
    created() {
        // Keep the plugin instance out of Vue's reactive data.
        this.backstretchInstance = null;
    },
    mounted() {
        this.setBackStretch();
    },
    methods: {
        async setBackStretch() {
            try {
                await waitFor(() => this.enabled !== null);
            } catch (error) {
                console.error(error);
            }

            if (!this.enabled) {
                return;
            }
            const { opacity, slug, offset } = this;
            if (slug) {
                const imgUrl = `api/v2/series/${slug}/asset/fanart?api_key=${this.apiKey}`;

                // If no element is supplied, attaches to `<body>`
                this.backstretchInstance = $.backstretch(imgUrl);
                const { $wrap } = this.backstretchInstance;
                $wrap.css('top', offset);
                $wrap.css('opacity', opacity).fadeIn(500);
            }
        },
        removeBackStretch() {
            const { backstretchInstance } = this;
            // Another page may have replaced or removed the shared background.
            if (backstretchInstance && backstretchInstance === $('body').data('backstretch')) {
                backstretchInstance.destroy();
            }
            this.backstretchInstance = null;
        }
    },
    destroyed() {
        this.removeBackStretch();
    },
    activated() {
        this.setBackStretch();
    },
    deactivated() {
        this.removeBackStretch();
    },
    watch: {
        opacity(newOpacity) {
            const { backstretchInstance } = this;
            if (backstretchInstance && backstretchInstance === $('body').data('backstretch')) {
                const { $wrap } = backstretchInstance;
                $wrap.css('opacity', newOpacity).fadeIn(500);
            }
        }
    }
};
</script>
