<script type="text/x-template" id="asset-template">
    <img v-if="!link" :src="src" :class="cls">
    <app-link v-else :href="href">
        <img :src="src" :class="cls">
    </app-link>
</script>
<script>
Vue.component('asset', {
    mixins: [ window.vueInViewportMixin ],
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
        cls: String
    },
    data() {
        return {
            isVisible: false
        };
    },
    computed: {
        src() {
            const {seriesSlug, type, isVisible} = this;
            const apiRoot = document.getElementsByTagName('body')[0].getAttribute('api-root');
            const apiKey = document.getElementsByTagName('body')[0].getAttribute('api-key');

            if (!isVisible || !seriesSlug || !type) {
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
    template: `#asset-template`
});
</script>
