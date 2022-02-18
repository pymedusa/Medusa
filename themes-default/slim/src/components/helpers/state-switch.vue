<template>
    <img v-bind="{ src, alt }" height="16" width="16" @click="$emit('click')">
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

</style>
