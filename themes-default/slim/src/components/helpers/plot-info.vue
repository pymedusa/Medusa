<template>
    <img v-if="description !== ''" src="images/info32.png" width="16" height="16" :class="plotInfoClass" alt=""
         v-tooltip.right="{content: description}">
</template>
<script>
import { VTooltip } from 'v-tooltip';

export default {
    name: 'plot-info',
    directives: {
        tooltip: VTooltip
    },
    props: {
        description: {
            type: String,
            required: true
        }
    },
    computed: {
        plotInfoClass() {
            return this.description === '' ? 'plotInfoNone' : 'plotInfo';
        }
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
