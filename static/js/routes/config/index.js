const medusa = require('../../medusa');
const backupRestore = require('./backup-restore');
const info = require('./info');
const init = require('./init');
const notifications = require('./notifications');
const postProcessing = require('./post-processing');
const search = require('./search');
const subtitles = require('./subtitles');

const index = () => {
    if ($('input[name="proxy_setting"]').val().length === 0) {
        $('input[id="proxy_indexers"]').prop('checked', false);
        $('label[for="proxy_indexers"]').hide();
    }

    $('#theme_name').on('change', async event => {
        const theme = $('#theme-stylesheet');
        const oldThemeName = theme.attr('href').split('/').pop().split('.')[0];
        const newThemeName = $(event.currentTarget).val();

        await medusa.config({ theme: { name: newThemeName } });

        theme[0].href = theme[0].href.replace(oldThemeName, newThemeName);
    });

    $('input[name="proxy_setting"]').on('input', event => {
        if ($(event.currentTarget).val().length === 0) {
            $('input[id="proxy_indexers"]').prop('checked', false);
            $('label[for="proxy_indexers"]').hide();
        } else {
            $('label[for="proxy_indexers"]').show();
        }
    });

    $('#log_dir').fileBrowser({
        title: 'Select log file folder location'
    });
};

module.exports = {
    index,
    backupRestore,
    info,
    init,
    notifications,
    postProcessing,
    search,
    subtitles
};
