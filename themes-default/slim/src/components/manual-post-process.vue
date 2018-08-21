<script>
export default {
    name: 'manual-post-process',
    template: '#manual-post-process-template',
    metaInfo: {
        title: 'Post Processing'
    },
    data() {
        return {
            header: 'Post Processing'
        };
    },
    mounted() {
        $('#episodeDir').fileBrowser({
            title: 'Select Unprocessed Episode Folder',
            key: 'postprocessPath'
        });
    }
};
</script>
