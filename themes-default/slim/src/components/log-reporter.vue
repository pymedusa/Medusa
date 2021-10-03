<template>
    <div id="log-reporter" class="row">
        <div class="col-md-12">
            <template v-if="logs.length > 0">
                <pre>
                    <div v-for="(log, idx) in logs" :key="idx">{{log}}</div>
                </pre>
            </template>
            <template v-else>
                <pre>There are no events to display</pre>
            </template>
        </div>
    </div>
</template>

<script>
import { api } from '../api';
import { mapState } from 'vuex';

export default {
    name: 'log-reporter',
    props: {
        level: {
            type: String,
            default: '30'
        }
    },
    data() {
        return {
            logs: []
        };
    },
    mounted() {
        this.unwatchProp = this.$watch('loggingLevels', _ => {
            this.unwatchProp();
            this.getLogs();
        });
    },
    computed: {
        ...mapState({
            loggingLevels: state => state.config.general.logs.loggingLevels
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
        async getLogs() {
            const { logLevel } = this;
            try {
                const { data } = await api.get('logreporter', { params: { level: logLevel } });
                this.logs = data;
            } catch (error) {
                this.$snotify.error(
                    `Error while trying to get logs with level ${logLevel}`,
                    'Error'
                );
            }
        }
    }
};
</script>

<style>
</style>
