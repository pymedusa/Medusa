<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-syno2" title="Synology Indexer"></span>
            <h3><app-link href="http://synology.com/">Synology Notifier</app-link></h3>
            <p>Synology Notifier is the notification system of Synology DSM</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_synologynotifier"
                    :explanations="['Send notifications to the Synology Notifier?', 'Note: requires Medusa to be running on your Synology DSM.']"
                    @change="save()" >
                </config-toggle-slider>
                <div v-show="enabled" id="content-use-synology-notifier">
                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="synology_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="synology_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()"/>
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'synology-indexer',
    data: () => ({
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null
    }),
    methods: {
        save() {},
        test() {}
    }
}
</script>

<style>

</style>
