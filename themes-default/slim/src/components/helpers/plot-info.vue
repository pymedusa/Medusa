<template>
    <img src="images/info32.png" width="16" height="16" :class="plotInfoClass" alt="" />
</template>
<script>

export default {
    name: 'plot-info',
    props: {
        description: {
            type: String,
            required: true
        },
        showSlug: {
            type: String,
            required: true
        },
        season: {
            type: [Number, String],
            required: true
        },
        episode: {
            type: [Number, String],
            required: true
        }
    },
    computed: {
        plotInfoClass() {
            return this.description !== '' ? 'plotInfo' : 'plotInfoNone';
        }
    },
    mounted() {
        const { description, $el, showSlug, season, episode } = this;
        if (description === '') {
            return false;
        }
        $($el).qtip({
            content: {
                text: description
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
