<script>
import { mapState } from 'vuex';

import { webRoot, apiKey } from '../api';
import { waitFor } from '../utils/core';

export default {
    name: 'backstretch',
    render: h => h(), // Doesn't render anything
    props: {
        slug: String
    },
    data() {
        return {
            created: false
        };
    },
    computed: {
        ...mapState({
            enabled: state => state.config.layout.fanartBackground,
            opacity: state => state.config.layout.fanartBackgroundOpacity
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
    async mounted() {
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
            const imgUrl = `${webRoot}/api/v2/series/${slug}/asset/fanart?api_key=${apiKey}`;

            // If no element is supplied, attaches to `<body>`
            const { $wrap } = $.backstretch(imgUrl);
            $wrap.css('top', offset);
            $wrap.css('opacity', opacity).fadeIn(500);
            this.created = true;
        }
    },
    destroyed() {
        if (this.created) {
            $.backstretch('destroy');
        }
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
