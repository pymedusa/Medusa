const state = require('../../state');

const backupRestore = () => {
    $('#Backup').on('click', () => {
        $('#Backup').prop('disabled', true);
        $('#Backup-result').html(state.components.loading);

        const backupDir = $('#backupDir').val();
        $.get('config/backuprestore/backup', {
            backupDir
        }).done(data => {
            $('#Backup-result').html(data);
            $('#Backup').prop('disabled', false);
        });
    });
    $('#Restore').on('click', () => {
        $('#Restore').prop('disabled', true);
        $('#Restore-result').html(state.components.loading);

        const backupFile = $('#backupFile').val();
        $.get('config/backuprestore/restore', {
            backupFile
        }).done(data => {
            $('#Restore-result').html(data);
            $('#Restore').prop('disabled', false);
        });
    });

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
};

module.exports = backupRestore;
