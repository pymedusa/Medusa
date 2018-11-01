<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-syno1" title="Synology"></span>
            <h3><app-link href="http://synology.com/">Synology</app-link></h3>
            <p>The Synology DiskStation NAS.</p>
            <p>Synology Indexer is the daemon running on the Synology NAS to build its media database.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="HTTPS" id="use_synoindex" :explanations="['Note: requires Medusa to be running on your Synology NAS.']" @change="save()"/>
                <div v-show="enabled" id="content_use_synoindex">
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'synology',
    data: () => ({
        enabled: null
    }),
    methods: {
        save() {},
        test() {}
    }
}
</script>

<style>

</style>
