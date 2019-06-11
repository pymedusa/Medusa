<script>
export default {
    name: 'manual-post-process',
    template: '#manual-post-process-template',
    mounted() {
        $('#episodeDir').fileBrowser({
            title: 'Select Unprocessed Episode Folder',
            key: 'postprocessPath'
        });
    }
};
</script>

<style>

</style>
