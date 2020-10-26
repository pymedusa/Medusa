<template>
    <div class="select-list">
        <div class="wrapper">
            <div v-for="customLog of customLogs" :key="customLog.identifier">
                <div class="level">
                    <select v-model="customLog.level" @input="saveLogs($event, customLog.identifier)">
                        <option :value="option.value" v-for="option in levels"
                                :key="option.value">{{ option.text }}
                        </option>
                    </select>
                </div>

                <div class="identifier">{{customLog.identifier}}</div>
            </div>
        </div>
    </div>
</template>
<script>

import { mapActions, mapState } from 'vuex';

export default {
    name: 'custom-logs',
    data() {
        return {
            levels: [
                { value: 10, text: 'DEBUG' },
                { value: 20, text: 'INFO' },
                { value: 30, text: 'WARNING' },
                { value: 40, text: 'ERROR' },
                { value: 50, text: 'CRITICAL' },
                { value: 0, text: 'DEFAULT' }
            ]
        };
    },
    computed: {
        ...mapState({
            logs: state => state.config.general.logs
        }),
        customLogs: {
            get() {
                // Help convert custom logs from object to array.
                const { logs } = this;
                return Object.keys(logs.custom).map(key => ({ identifier: key, level: logs.custom[key] }));
            },
            set(logs) {
                // No need to convert back to object, as the api requires an array of objects.
                const { setCustomLogs } = this;
                setCustomLogs(logs);
            }
        }
    },
    methods: {
        ...mapActions({
            setCustomLogs: 'setCustomLogs'
        }),
        saveLogs(event, identifier) {
            const { customLogs } = this;

            // Remove the currentLog from the array.
            const customLogsCopy = customLogs.map(log => {
                if (log.identifier === identifier) {
                    log.level = Number(event.target.value);
                }
                return log;
            });

            // Trigger the setter.
            this.customLogs = customLogsCopy;
        }
    }
};
</script>
<style scoped>
div.wrapper > div {
    margin-bottom: 5px;
}

div.identifier {
    float: none;
    width: auto;
    overflow: hidden;
}

div.level {
    float: right;
}
</style>
