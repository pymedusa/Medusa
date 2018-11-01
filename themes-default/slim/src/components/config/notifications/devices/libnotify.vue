<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-libnotify" title="Libnotify"></span>
            <h3><app-link href="http://library.gnome.org/devel/libnotify/">Libnotify</app-link></h3>
            <p>The standard desktop notification API for Linux/*nix systems.  This notifier will only function if the pynotify module is installed (Ubuntu/Debian package <app-link href="apt:python-notify">python-notify</app-link>).</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_libnotify_client" :explanations="['Send Libnotify notifications?']" @change="save()"/>
                <div v-show="enabled" id="content-use-libnotify">

                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="libnotify_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="libnotify_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="libnotify_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()"/>

                    <div class="testNotification" id="testLibnotify-result">Click below to test.</div>
                    <input  class="btn-medusa" type="button" value="Test Libnotify" id="testLibnotify" @click="test"/>
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'libnotify',
    data: () => ({
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null
    }),
    methods: {
        save() {},
        test() {
            $('#testLibnotify-result').html(MEDUSA.config.loading);
            $.get('home/testLibnotify', data => {
                $('#testLibnotify-result').html(data);
            });
        }
    }
}
</script>

<style>

</style>
