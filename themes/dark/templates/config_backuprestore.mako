<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        metaInfo: {
            title: 'Config - Backup/Restore'
        },
        data() {
            return {
                header: 'Backup/Restore',
                backup: {
                    disabled: false,
                    status: '',
                    // dir: ''
                },
                restore: {
                    disabled: false,
                    status: '',
                    // file: ''
                }
            };
        },
        mounted() {
            /*
            @FIXME: Can't convert these to use the file-browser component
                    because it can't handle more than one file browser per page.
                    file-browser needs to be pure JavaScript / Vue, without any jQuery.
            */
            $('#backupDir').fileBrowser({
                title: 'Select backup folder to save to',
                key: 'backupPath'
            });
            $('#backupFile').fileBrowser({
                title: 'Select backup files to restore',
                key: 'backupFile',
                includeFiles: 1
            });
            $('#config-components').tabs();
        },
        methods: {
            runBackup() {
                const { backup } = this;
                const dir = $('#backupDir').val();

                if (!dir) return;

                backup.disabled = true;
                backup.status = MEDUSA.config.loading;

                $.get('config/backuprestore/backup', {
                    backupDir: dir
                }).done(data => {
                    backup.status = data;
                    backup.disabled = false;
                });
            },
            runRestore() {
                const { restore } = this;
                const dir = $('#backupFile').val();

                if (!dir) return;

                restore.disabled = true;
                restore.status = MEDUSA.config.loading;

                $.get('config/backuprestore/restore', {
                    backupFile: dir
                }).done(data => {
                    restore.status = data;
                    restore.disabled = false;
                });
            }
        }
    });
};
</script>
</%block>
<%block name="content">
<h1 class="header">{{header}}</h1>
<div id="config">
    <div id="config-content">
        <form name="configForm" method="post" action="config/backuprestore">
            <div id="config-components">
                <ul>
                    <li><app-link href="#backup">Backup</app-link></li>
                    <li><app-link href="#restore">Restore</app-link></li>
                </ul>
                <div id="backup" class="component-group clearfix">
                    <div class="component-group-desc">
                        <h3>Backup</h3>
                        <p><b>Backup your main database file and config.</b></p>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            Select the folder you wish to save your backup file to:
                            <br><br>
                            <input type="text" name="backupDir" id="backupDir" class="form-control input-sm input350"/>
                            <input @click="runBackup" :disabled="backup.disabled" class="btn-medusa btn-inline" type="button" value="Backup" id="Backup" />
                            <br>
                        </div>
                        <div v-html="backup.status" class="Backup" id="Backup-result"></div>
                    </fieldset>
                </div><!-- /component-group1 //-->
                <div id="restore" class="component-group clearfix">
                    <div class="component-group-desc">
                        <h3>Restore</h3>
                        <p><b>Restore your main database file and config.</b></p>
                    </div>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            Select the backup file you wish to restore:
                            <br><br>
                            <input type="text" name="backupFile" id="backupFile" class="form-control input-sm input350"/>
                            <input @click="runRestore" :disabled="restore.disabled" class="btn-medusa btn-inline" type="button" value="Restore" id="Restore" />
                            <br>
                        </div>
                        <div v-html="restore.status" class="Restore" id="Restore-result"></div>
                    </fieldset>
                </div><!-- /component-group2 //-->
            </div><!-- /config-components -->
        </form>
    </div>
</div>
<div class="clearfix"></div>
</%block>
