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
            return percentage === 100 ? 100 : percentage > 80 ? 80 : percentage > 60 ? 60 : percentage > 40 ? 40 : 20;
        }
    }
};
</script>
<style scoped>
.progressbar {
    position: relative;
}
</style>
