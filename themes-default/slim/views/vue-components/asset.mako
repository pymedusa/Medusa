<script type="text/x-template" id="asset-template">
    <img v-if="!link" :src="src" :class="cls" @error="error = true">
    <app-link v-else :href="href">
        <img :src="src" :class="cls" @error="error = true">
    </app-link>
</script>
<script>
const { VueInViewportMixin } = window;
const assetComponent = {
    name: 'asset',
    mixins: [ VueInViewportMixin ],
    props: {
        seriesSlug: String,
        type: {
            type: String,
            required: true
        },
        default: String,
        link: {
            type: Boolean,
            default: false
        },
        cls: String,
        lazy: {
            type: Boolean,
            default: true
        }
    },
    data() {
        return {
            isVisible: false,
            error: false
        };
    },
    computed: {
        src() {
            const { error, seriesSlug, type, isVisible, lazy } = this;
            const apiRoot = document.body.getAttribute('web-root') + '/api/v2/';
            const apiKey = document.body.getAttribute('api-key');

            if (error || lazy && !isVisible || !seriesSlug || !type) {
                return this.default;
            }

            return apiRoot + 'series/' + seriesSlug + '/asset/' + type + '?api_key=' + apiKey;
        },
        href() {
            // Compute a link to the full asset, if applicable
            if (this.link) return this.src.replace('Thumb', '');
        }
    },
    watch: {
        'inViewport.now': function(visible) {
            if (!this.isVisible && visible) {
                this.isVisible = visible;
            }
        }
    },
    template: '#asset-template'
};

Vue.component('asset', assetComponent);
window.components.push(assetComponent);
</script>
