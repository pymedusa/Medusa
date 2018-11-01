<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-pushalot" title="Pushalot"></span>
            <h3><app-link href="https://pushalot.com">Pushalot</app-link></h3>
            <p>Pushalot is a platform for receiving custom push notifications to connected devices running Windows Phone or Windows 8.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_pushalot" :explanations="['Send Pushalot notifications?']" @change="save()"/>
                <div v-show="enabled" id="content-use-pushalot-client">

                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="pushalot_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="pushalot_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="pushalot_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()"/>
                    <config-textbox v-model="authToken" label="Pushalot authorization token" id="pushalot_authorizationtoken" :explanations="['authorization token of your Pushalot account.']" @change="save()"/>

                    <div class="testNotification" id="testPushalot-result">Click below to test.</div>
                    <input type="button" class="btn-medusa" value="Test Pushalot" id="testPushalot" @click="test"/>
                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'pushalot',
    data: () => ({
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null,
        authToken: null
    }),
    methods: {
        save() {},
        test() {
            const pushalot = {};
            pushalot.authToken = $.trim($('#pushalot_authorizationtoken').val());
            if (!pushalot.authToken) {
                $('#testPushalot-result').html('Please fill out the necessary fields above.');
                $('#pushalot_authorizationtoken').addClass('warning');
                return;
            }
            $('#pushalot_authorizationtoken').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testPushalot-result').html(MEDUSA.config.loading);
            $.get('home/testPushalot', {
                authorizationToken: pushalot.authToken
            }).done(data => {
                $('#testPushalot-result').html(data);
                $('#testPushalot').prop('disabled', false);
            });
        }
    }
}
</script>

<style>

</style>
