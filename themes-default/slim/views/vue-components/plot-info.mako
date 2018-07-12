<script type="text/x-template" id="plot-info-template">
    <img src="images/info32.png" width="16" height="16" :class="plotInfoClass" alt="" />
</script>
<script>
Vue.component('plot-info', {
    props: {
        hasPlot: Boolean,
        seriesSlug: {
            type: String,
            required: true
        },
        season: {
            type: String,
            required: true
        },
        episode: {
            type: String,
            required: true
        }
    },
    computed: {
        plotInfoClass() {
            return this.hasPlot ? 'plotInfo' : 'plotInfoNone';
        }
    },
    mounted() {
        const {hasPlot, seriesSlug, season, episode} = this;
        if (!hasPlot) {
            return false;
        }
        $(this.$el).qtip({
            content: {
                text(event, qt) {
                    api.get('series/' + seriesSlug + '/episode/s' + season + 'e' + episode + '/description').then(response => {
                        // Set the tooltip content upon successful retrieval
                        qt.set('content.text', response.data);
                    }, xhr => {
                        // Upon failure... set the tooltip content to the status and error value
                        qt.set('content.text', 'Error while loading plot: ' + xhr.status + ': ' + xhr.statusText);
                    });
                    return 'Loading...';
                }
            },
            show: {
                solo: true
            },
            position: {
                my: 'left center',
                adjust: {
                    y: -10,
                    x: 2
                }
            },
            style: {
                tip: {
                    corner: true,
                    method: 'polygon'
                },
                classes: 'qtip-rounded qtip-shadow ui-tooltip-sb'
            }
        });
    },
    template: `#plot-info-template`
});
</script>
