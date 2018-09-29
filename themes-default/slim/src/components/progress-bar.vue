<template>
    <div v-bind="{ title }" class="progressbar hidden-print">
        <div v-if="text" class="progressbarText">{{ text }}</div>
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
        classToAdd() {
            const percentage = Number(this.percentage);
            return percentage === 100 ? 100 : percentage > 80 ? 80 : percentage > 60 ? 60 : percentage > 40 ? 40 : 20;
        }
    },
    mounted() {
        $(this.$el).progressbar({
            value: this.percentage
        });
        $(this.$el).find('.ui-progressbar-value').addClass('progress-' + this.classToAdd);
    }
}
</script>
<style scoped>
.progressbar {
    position: relative;
}
</style>
