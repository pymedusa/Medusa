const postProcess = () => {
    $('#episodeDir').fileBrowser({
        title: 'Select Unprocessed Episode Folder',
        key: 'postprocessPath'
    });
};

module.exports = postProcess;
