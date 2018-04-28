<script type="text/x-template" id="asset-template">
    <img :src="src">
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
        default: String
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

            if (!isVisible) {
                return this.default;
            }

            return apiRoot + 'series/' + seriesSlug + '/asset/' + type + '?api_key=' + apiKey;
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
