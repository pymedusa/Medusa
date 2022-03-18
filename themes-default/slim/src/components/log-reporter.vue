<template>
    <div id="log-reporter">
        <div class="row">
            <div class="col-md-12">
                <!-- Toggle auto update -->
                <div class="show-option">
                    <button @click="autoUpdate = !autoUpdate" type="button" class="btn-medusa btn-inline">
                        <i :class="`glyphicon glyphicon-${autoUpdate ? 'pause' : 'play'}`" />
                        {{ autoUpdate ? 'Pause' : 'Resume' }}
                    </button>
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-md-12">
                <template v-if="logs.length > 0">
                    <pre><div v-for="(log, idx) in logs" :key="idx">{{log}}</div></pre>
                </template>
                <template v-else>
                    <pre>There are no events to display</pre>
                </template>
            </div>
        </div>
    </div>
</template>

<script>
import { mapState } from 'vuex';

export default {
    name: 'log-reporter',
    props: {
        level: {
            type: String,
            default: '40' // Default level of ERROR
        }
    },
    data() {
        return {
            logs: [],
            autoUpdate: true,
            autoUpdateTimer: null
        };
    },
    mounted() {
        if (this.autoUpdate) {
            this.autoUpdateTask();
        } else {
            this.fetchLogs();
        }
    },
    computed: {
        ...mapState({
            loggingLevels: state => state.config.general.logs.loggingLevels,
            client: state => state.auth.client
        }),
        header() {
            const { logLevel, loggingLevels } = this;
            if (logLevel === loggingLevels.warning) {
                return 'Warning Logs';
            }
            return 'Error Logs';
        },
        logLevel() {
            return this.$route.query.level || this.level;
        }
    },
    methods: {
        async fetchLogs() {
            const { client, logLevel, loggingLevels } = this;
            if (Object.keys(this.loggingLevels).length === 0) {
                return;
            }

            const logLevelString = Object.keys(loggingLevels).find(
                key => loggingLevels[key] === Number(logLevel)
            ).toUpperCase();

            try {
                const { data } = await client.api.get('log/reporter', { params: { level: logLevelString } });
                this.logs = data;
                return true;
            } catch (error) {
                this.$snotify.error(
                    `Error while trying to get logs with level ${logLevel}`,
                    'Error'
                );
                return false;
            }
        },
        async autoUpdateTask(errors = 0) {
            if (this.autoUpdate) {
                const result = await this.fetchLogs();
                // Increment if false
                errors += Number(!result);
                // Stop after 5 network errors
                if (errors < 5) {
                    this.autoUpdateTimer = setTimeout(this.autoUpdateTask, 1500, errors);
                } else {
                    this.autoUpdate = false;
                    this.autoUpdateTimer = null;
                }
            } else {
                this.autoUpdateTimer = null;
            }
        }
    },
    watch: {
        logLevel() {
            this.fetchLogs();
        },
        autoUpdate() {
            this.autoUpdateTask();
        }
    }
};
</script>

<style scoped>
button {
    margin-bottom: 1em;
}
</style>
