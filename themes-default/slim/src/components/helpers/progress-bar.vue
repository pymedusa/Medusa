<template>
    <div v-bind="{ title }" class="progressbar hidden-print ui-progressbar ui-corner-all ui-widget ui-widget-content" role="progressbar">
        <div v-if="text" class="progressbarText">{{ text }}</div>
        <div v-show="normalisedPercentage >= 1" :class="['ui-progressbar-value', 'ui-corner-left', 'ui-widget-header', 'progress-' + normalisedPercentage]" :style="{ width: `${percentage}%` }" />
    </div>
</template>
<script>
export default {
    props: {
        text: String,
        title: String,
        percentage: [String, Number]
    },
    computed: {
        normalisedPercentage() {
            const percentage = Number(this.percentage);
            if (percentage === 100) {
                return 100;
            }

            if (percentage > 80) {
                return 80;
            }

            if (percentage > 60) {
                return 60;
            }

            if (percentage > 40) {
                return 40;
            }

            return 20;
        }
    }
};
</script>
<style scoped>
.progressbar {
    position: relative;
}
</style>
