<template>
    <iframe :src="frameSrc" class="irc-frame loading-spinner"></iframe>
</template>

<script>
import { mapState } from 'vuex';

export default {
    name: 'IRC',
    computed: {
        ...mapState({
            configLoaded: state => state.config.pythonVersion !== null,
            gitUsername: state => state.config.gitUsername
        }),
        frameSrc() {
            const { configLoaded, gitUsername } = this;
            if (!configLoaded) {
                return undefined;
            }
            const username = gitUsername || 'MedusaUI|?';
            return `https://kiwiirc.com/client/irc.freenode.net/?nick=${username}&theme=basic#pymedusa`;
        }
    }
};
</script>

<style scoped>
.irc-frame {
    width: 100%;
    height: 500px;
    border: 1px #000 solid;
}

.loading-spinner {
    background-position: center center;
    background-repeat: no-repeat;
}
</style>
