MEDUSA.home.postProcess = function() { // eslint-disable-line no-undef
    $('#episodeDir').fileBrowser({
        title: 'Select Unprocessed Episode Folder',
        key: 'postprocessPath'
    });
};
