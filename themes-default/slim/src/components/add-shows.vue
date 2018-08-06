<template>
    <div id="addShowPortal">
        <app-link href="addShows/newShow/" id="btnNewShow" class="btn-medusa btn-large">
            <div class="button"><div class="add-list-icon-addnewshow"></div></div>
            <div class="buttontext">
                <h3>Add New Show</h3>
                <p>For shows that you haven't downloaded yet, this option finds a show on your preferred indexer, creates a directory for it's episodes, and adds it to Medusa.</p>
            </div>
        </app-link>

        <app-link href="addShows/existingShows/" id="btnExistingShow" class="btn-medusa btn-large">
            <div class="button"><div class="add-list-icon-addexistingshow"></div></div>
            <div class="buttontext">
                <h3>Add Existing Shows</h3>
                <p>Use this option to add shows that already have a folder created on your hard drive. Medusa will scan your existing metadata/episodes and add the show accordingly.</p>
            </div>
        </app-link>
    </div>
</template>
<script>
import AppLink from './app-link.vue';

module.exports = {
    name: 'addShows',
    components: {
        AppLink
    },
    computed: {
        header() {
            return this.$route.meta.header;
        }
    }
};
</script>
<style>
/* placeholder */
</style>
