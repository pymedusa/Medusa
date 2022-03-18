<template>
    <div id="update">
        <template v-if="system.runsInDocker">
            <span v-if="system.newestVersionMessage">{{system.newestVersionMessage}}</span>
            <span v-else>You are running Medusa in docker. To update, please pull a new image from the docker hub</span>
        </template>
        <template v-else-if="!startUpdate">
            <span>Medusa will automatically create a backup before you update. Are you sure you want to update?</span>
            <button id="update-now" class="btn-medusa btn-danger" @click="performUpdate">Yes</button>
        </template>
        <template v-else>
            <div id="check_update">
                Checking if medusa needs an update
                <state-switch :theme="layout.themeName" :state="needUpdateStatus" />
            </div>
            <div v-if="needUpdateStatus === 'yes'" id="creating_backup">
                Waiting for Medusa to create a backup:
                <state-switch :theme="layout.themeName" :state="backupStatus" />
            </div>
            <div v-if="backupStatus === 'yes'" id="starting_update">
                Waiting for Medusa to update:
                <state-switch :theme="layout.themeName" :state="updateStatus" />
            </div>
            <div id="restart" v-if="updateStatus === 'yes'">
                <span>Update finished. Restart now?</span>
                <button id="update-now" class="btn-medusa btn-danger" @click="$router.push({ name: 'restart' })">Yes</button>
            </div>
        </template>
    </div>
</template>
<script>
import { mapState } from 'vuex';
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
            startUpdate: false,
            backupStatus: 'loading',
            updateStatus: 'loading',
            needUpdateStatus: 'loading'
        };
    },
    computed: {
        ...mapState({
            general: state => state.config.general,
            layout: state => state.config.layout,
            system: state => state.config.system,
            client: state => state.auth.client
        })
    },
    methods: {
        /**
         * Check if we need an update and start backup / update procedure.
         */
        async performUpdate() {
            this.startUpdate = true;

            try {
                await this.client.api.post('system/operation', { type: 'NEED_UPDATE' });
                this.needUpdateStatus = 'yes';
            } catch (error) {
                this.needUpdateStatus = 'no';
            }

            if (this.needUpdateStatus === 'yes') {
                try {
                    await this.client.api.post('system/operation', { type: 'BACKUP' }, { timeout: 1200000 });
                    this.backupStatus = 'yes';
                } catch (error) {
                    this.backupStatus = 'no';
                }
            }

            if (this.backupStatus === 'yes') {
                try {
                    await this.client.api.post('system/operation', { type: 'UPDATE' });
                    this.updateStatus = 'yes';
                } catch (error) {
                    this.updateStatus = 'no';
                }
            }
        }
    }
};
</script>
<style>
</style>
