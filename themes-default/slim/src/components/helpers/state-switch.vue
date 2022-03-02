<template>
    <svg v-if="state === 'loading'"
         class="animate-spin"
         :style="`width: ${iconSize}; height: ${iconSize};`"
         fill="none"
         viewBox="0 0 24 24"
    >
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
    <img v-else v-bind="{ src, alt }" height="16" width="16" @click="$emit('click')">
</template>
<script>
export default {
    name: 'state-switch',
    props: {
        /**
         * Theme for loading spinner
         */
        theme: {
            type: String,
            default: 'dark',
            validator: theme => [
                'dark',
                'light'
            ].includes(theme)
        },
        /**
         * Loading, yes or no
         * null, true or false
         */
        state: {
            required: true,
            validator: state => [
                'yes',
                'no',
                'loading',
                'true',
                'false',
                'null'
            ].includes(String(state))
        },
        iconSize: {
            required: false,
            default: '16px'
        }
    },
    computed: {
        src() {
            const { theme, realState: state } = this;
            return state === 'loading' ? `images/loading16-${theme || 'dark'}.gif` : `images/${state}16.png`;
        },
        alt() {
            const { realState: state } = this;
            return state.charAt(0).toUpperCase() + state.slice(1);
        },
        realState() {
            const { state } = this;
            if (['null', 'true', 'false'].includes(String(state))) {
                return {
                    null: 'loading',
                    true: 'yes',
                    false: 'no'
                }[String(state)];
            }
            return state;
        }
    }
};
</script>
<style>
.opacity-25 {
    opacity: 0.25;
}

.opacity-75 {
    opacity: 0.75;
}

.animate-spin {
    animation: spin 1s linear infinite;
    color: green;
}

@keyframes spin {
    from {
        transform: rotate(0deg);
    }

    to {
        transform: rotate(360deg);
    }
}
</style>
