const MEDUSA = require('../core');

MEDUSA.home.postProcess = function() {
    $('#episodeDir').fileBrowser({
        title: 'Select Unprocessed Episode Folder',
        key: 'postprocessPath'
    });
};
