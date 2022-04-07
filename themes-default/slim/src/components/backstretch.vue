<script>
import { mapState } from 'vuex';
import { waitFor } from '../utils/core';

export default {
    name: 'backstretch',
    render: h => h(), // Doesn't render anything
    props: {
        slug: String
    },
    data() {
        return {
            created: false,
            wrapper: null
        };
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
                const { $wrap } = $.backstretch(imgUrl);
                $wrap.css('top', offset);
                $wrap.css('opacity', opacity).fadeIn(500);
                this.created = true;
                this.wrapper = $wrap;
            }
        },
        removeBackStretch() {
            if (this.created) {
                $.backstretch('destroy');
                this.created = false;
            }
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
            if (this.created) {
                const { $wrap } = $('body').data('backstretch');
                $wrap.css('opacity', newOpacity).fadeIn(500);
            }
        }
    }
};
</script>
