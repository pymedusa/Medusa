<template>
    <div id="config">
        <div id="config-content">
            <form name="configForm" method="post" action="config/backuprestore">
                <vue-tabs>
                    <v-tab key="backup" title="Backup">
                        <div id="backup" class="component-group clearfix">
                            <div class="component-group-desc-legacy">
                                <h3>Backup</h3>
                                <p><b>Backup your main database file and config.</b></p>
                            </div>
                            <fieldset class="component-group-list">
                                <div class="field-pair">
                                    Select the folder you wish to save your backup-file to:
                                    <br><br>
                                    <file-browser name="backupDir" title="Select folder to save to" local-storage-key="backupPath" @update="backup.dir = $event" />
                                    <br>
                                    <input @click="runBackup" :disabled="backup.disabled" class="btn-medusa btn-inline" type="button" value="Backup" id="Backup">
                                    <br>
                                </div>
                                <state-switch v-if="backup.status === 'loading'" state="loading" />
                                <div v-else v-html="backup.status" class="Restore" id="Backup-result" />
                            </fieldset>
                        </div><!-- /component-group1 //-->
                    </v-tab>

                    <v-tab key="restore" title="Restore">
                        <div id="restore" class="component-group clearfix">
                            <div class="component-group-desc-legacy">
                                <h3>Restore</h3>
                                <p><b>Restore your main database file and config.</b></p>
                            </div>
                            <fieldset class="component-group-list">
                                <div class="field-pair">
                                    Select the backup file you wish to restore:
                                    <br><br>
                                    <file-browser name="backupFile" title="Select backup file to restore" local-storage-key="backupFile" include-files @update="restore.file = $event" />
                                    <br>
                                    <input @click="runRestore" :disabled="restore.disabled" class="btn-medusa btn-inline" type="button" value="Restore" id="Restore">
                                    <br>
                                </div>
                                <state-switch v-if="restore.status === 'loading'" state="loading" />
                                <div v-else v-html="restore.status" class="Restore" id="Restore-result" />
                            </fieldset>
                        </div><!-- /component-group2 //-->

                    </v-tab>
                </vue-tabs>
            </form>
        </div>
    </div>
</template>

<script>
import { mapState } from 'vuex';
import { FileBrowser, StateSwitch } from './helpers';
import { VueTabs, VTab } from 'vue-nav-tabs/dist/vue-tabs.js';

export default {
    name: 'config-backup-restore',
    components: {
        FileBrowser,
        StateSwitch,
        VueTabs,
        VTab
    },
    data() {
        return {
            backup: {
                disabled: false,
                status: '',
                dir: ''
            },
            restore: {
                disabled: false,
                status: '',
                file: ''
            }
        };
    },
    beforeMount() {
        $('#config-components').tabs();
    },
    computed: {
        ...mapState({
            client: state => state.auth.client
        })
    },
    methods: {
        async runBackup() {
            const { backup } = this;

            if (!backup.dir) {
                return;
            }

            backup.disabled = true;
            backup.status = 'loading';

            try {
                const { data } = await this.client.api.post('system/operation', {
                    type: 'BACKUPTOZIP', backupDir: backup.dir
                }, { timeout: 180000 });
                backup.status = data.result;
                backup.disabled = false;
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to create backup',
                    'Error'
                );
                backup.status = 'Failed trying to create the backup or it timed out. Check your logs.';
            }
        },
        async runRestore() {
            const { restore } = this;

            if (!restore.file) {
                return;
            }

            restore.disabled = true;
            restore.status = 'loading';

            try {
                const { data } = await this.client.api.post('system/operation', {
                    type: 'RESTOREFROMZIP', backupFile: restore.file
                }, { timeout: 180000 });

                restore.status = data.result;
                restore.disabled = false;
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to restore backup',
                    'Error'
                );
                restore.status = 'Failed trying to restore the backup or it timed out. Check your logs.';
            }
        }
    }
};
</script>

<style>
</style>
