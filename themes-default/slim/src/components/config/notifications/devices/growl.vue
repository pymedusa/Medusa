<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-growl" title="Growl"></span>
            <h3><app-link href="http://growl.info/">Growl</app-link></h3>
            <p>A cross-platform unobtrusive global notification system.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_growl_client" :explanations="['Send growl Home Theater notifications?']" @change="save()"/>
                <div v-show="enabled" id="content-use-growl-client">

                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="growl_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="growl_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="growl_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()"/>
                    <config-textbox v-model="host" label="Growl IP:Port" id="growl_host" :explanations="['host running Growl (eg. 192.168.1.100:23053)']" @change="save()"/>
                    <config-textbox v-model="password" label="Password" id="growl_password" :explanations="['may leave blank if Medusa is on the same host.', 'otherwise Growl requires a password to be used.']" @change="save()"/>

                    <div class="testNotification" id="testGrowl-result">Click below to register and test Growl, this is required for Growl notifications to work.</div>
                    <input  class="btn-medusa" type="button" value="Register Growl" id="testGrowl" @click="test"/>
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'growl',
    data: () => ({
        enabled: null,
        host: null,
        password: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null
    }),
    methods: {
        save() {},
        test() {
            const growl = {};
            growl.host = $.trim($('#growl_host').val());
            growl.password = $.trim($('#growl_password').val());
            if (!growl.host) {
                $('#testGrowl-result').html('Please fill out the necessary fields above.');
                $('#growl_host').addClass('warning');
                return;
            }
            $('#growl_host').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testGrowl-result').html(MEDUSA.config.loading);
            $.get('home/testGrowl', {
                host: growl.host,
                password: growl.password
            }).done(data => {
                $('#testGrowl-result').html(data);
                $('#testGrowl').prop('disabled', false);
            });
        }
    }
}
</script>

<style>

</style>
