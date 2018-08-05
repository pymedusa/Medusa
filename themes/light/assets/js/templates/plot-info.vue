<template>
    <img src="images/info32.png" width="16" height="16" :class="plotInfoClass" alt="" />
</template>
<script>
import { api } from '../api';

module.exports = {
    name: 'plot-info',
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
        const { $el, hasPlot, seriesSlug, season, episode } = this;
        if (!hasPlot) {
            return false;
        }
        $($el).qtip({
            content: {
                text(event, qt) {
                    api.get('series/' + seriesSlug + '/episodes/s' + season + 'e' + episode + '/description').then(response => {
                        // Set the tooltip content upon successful retrieval
                        qt.set('content.text', response.data);
                    }).catch(error => {
                        // Upon failure... set the tooltip content to the status and error value
                        const { response } = error;
                        const { status, statusText } = response;
                        qt.set('content.text', 'Error while loading plot: ' + status + ': ' + statusText);
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
    }
};
</script>
<style>
.plotInfo {
    cursor: help;
    float: right;
    position: relative;
    top: 2px;
}

.plotInfoNone {
    cursor: help;
    float: right;
    position: relative;
    top: 2px;
    opacity: 0.4;
}
</style>
