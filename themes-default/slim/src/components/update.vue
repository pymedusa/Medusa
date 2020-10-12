<template>
    <div id="update">
        <template v-if="!startUpdate">
            <span>Medusa will automatically create a backup before you update. Are you sure you want to update?</span>
            <button id="update-now" class="btn-medusa btn-danger" @click="backup">Yes</button>
        </template>
        <template v-else>
            <div id="creating_backup">
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
import { api } from '../api.js';
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
            updateStatus: 'loading'
        };
    },
    computed: {
        ...mapState({
            general: state => state.config.general,
            layout: state => state.config.layout
        })
    },
    methods: {
        async backup() {
            this.startUpdate = true;
            try {
                await api.post('system/operation', { type: 'BACKUP' }, { timeout: 1200000 });
                this.backupStatus = 'yes';
                this.update();
            } catch (error) {
                this.backupStatus = 'no';
            }
        },
        async update() {
            try {
                await api.post('system/operation', { type: 'UPDATE' });
                this.updateStatus = 'yes';
            } catch (error) {
                this.updateStatus = 'no';
            }
        }

    }
};
</script>
<style>
</style>
