<template>
    <div id="restart">
        <template v-if="!startRestart || (shutdown && !startShutdown)">
            <span>Are you sure you want to {{!shutdown ? 'restart' : 'shutdown'}}?</span>
            <button id="restart-now" class="btn-medusa btn-danger" @click="restart">Yes</button>
        </template>
        <template v-else-if="shutdown && startShutdown">
            Shutting down Medusa
        </template>
        <template v-else>
            <div id="shut_down_message">
                Waiting for Medusa to shut down:
                <state-switch :theme="layout.themeName" :state="status === 'shutting_down' ? 'loading' : 'yes'" />
            </div>
            <div id="restart_message" v-if="status === 'initializing' || status === 'restarted'">
                Waiting for Medusa to start again:
                <state-switch v-if="restartState" :theme="layout.themeName" :state="restartState" />
            </div>
            <div id="refresh_message" v-if="status === 'restarted'">
                Loading the default page: <state-switch :theme="layout.themeName" state="loading" />
            </div>
            <div id="restart_fail_message" v-if="status === 'failed'">
                Error: The restart has timed out, perhaps something prevented Medusa from starting again?
            </div>
        </template>
    </div>
</template>
<script>
import { mapState } from 'vuex';
import { api, apiRoute } from '../api.js';
import { StateSwitch } from './helpers';
/**
 * An object representing a restart component.
 * @typedef {Object} restart
 */
export default {
    name: 'restart',
    components: {
        StateSwitch
    },
    props: {
        shutdown: Boolean
    },
    data() {
        return {
            startRestart: false,
            startShutdown: false,
            status: '',
            currentPid: null
        };
    },
    computed: {
        ...mapState({
            general: state => state.config.general,
            systemPid: state => state.config.system.pid,
            layout: state => state.config.layout
        }),
        restartState() {
            const { status } = this;

            if (status === 'failed') {
                return 'no';
            }

            if (status === 'restarted') {
                return 'yes';
            }

            return 'loading';
        }
    },
    methods: {
        restart() {
            const { general, shutdown, systemPid } = this;
            const { defaultPage } = general;

            if (shutdown) {
                return this.shutdownMedusa();
            }

            const checkIsAlive = setInterval(() => {
                // @TODO: Move to API
                apiRoute.get('home/is_alive/')
                    .then(({ data }) => {
                        const { pid } = data;
                        if (!pid) {
                            // If it's still initializing then just wait and try again
                            this.status = 'initializing';
                        } else if (!systemPid || systemPid === pid) {
                            this.status = 'shutting_down';
                            this.currentPid = pid;
                        } else {
                            clearInterval(checkIsAlive);
                            this.status = 'restarted';
                            setTimeout(() => {
                                window.location.href = defaultPage + '/';
                            }, 5000);
                        }
                    })
                    .catch(() => {
                        this.status = 'initializing';
                    });
            }, 1000);

            this.startRestart = true;
            api.post('system/operation', { type: 'RESTART', pid: systemPid });
        },
        shutdownMedusa() {
            const { systemPid } = this;

            this.startShutdown = true;
            api.post('system/operation', { type: 'SHUTDOWN', pid: systemPid });
        }
    }
};
</script>
<style>
</style>
