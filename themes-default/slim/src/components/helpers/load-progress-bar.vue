<template>
    <div v-if="display" class="load-progress-bar-container alert alert-info hidden-print" role="status" aria-live="polite">
        <i class="loading-indicator glyphicon glyphicon-refresh" aria-hidden="true" />
        <span>{{loadMsg}}</span>
    </div>
</template>
<script>

export default {
    name: 'load-progress-bar',
    props: {
        display: Boolean,
        current: Number,
        total: Number,
        description: {
            type: String,
            default: 'Shows'
        }
    },
    computed: {
        loadMsg() {
            const { current, total, description } = this;
            return `Loaded ${current} out of ${total} ${description}`;
        }
    }
};
</script>
<style>
.load-progress-bar-container {
    position: fixed;
    bottom: 10px;
    right: 10px;
    z-index: 2;
    display: flex;
    align-items: center;
    margin: 0;
}

@media (max-width: 767px) {
    .load-progress-bar-container {
        right: 0;
        bottom: 0;
        justify-content: center;
        width: 100%;
        border-radius: 0;
    }
}

.loading-indicator {
    margin-right: 0.5em;
    animation: loading-indicator-spin 1s linear infinite;
}

@keyframes loading-indicator-spin {
    from {
        transform: rotate(0deg);
    }

    to {
        transform: rotate(360deg);
    }
}
</style>
