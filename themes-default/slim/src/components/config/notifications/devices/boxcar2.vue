<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-boxcar2" title="Boxcar 2"></span>
            <h3><app-link href="https://new.boxcar.io/">Boxcar 2</app-link></h3>
            <p>Read your messages where and when you want them!</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_boxcar2" :explanations="['Send boxcar2 notifications?']" @change="save()"/>
                <div v-show="enabled" id="content-use-boxcar2-client">

                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="boxcar2_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="boxcar2_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="boxcar2_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()"/>
                    <config-textbox v-model="accessToken" label="Boxcar2 Access token" id="boxcar2_accesstoken" :explanations="['access token for your Boxcar account.']" @change="save()"/>

                    <div class="testNotification" id="testBoxcar2-result">Click below to test.</div>
                    <input  class="btn-medusa" type="button" value="Test Boxcar" id="testBoxcar2" @click="test"/>
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'boxcar2',
    data: () => ({
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null,
        accessToken: null
    }),
    methods: {
        save() {},
        test() {
            const boxcar2 = {};
            boxcar2.accesstoken = $.trim($('#boxcar2_accesstoken').val());
            if (!boxcar2.accesstoken) {
                $('#testBoxcar2-result').html('Please fill out the necessary fields above.');
                $('#boxcar2_accesstoken').addClass('warning');
                return;
            }
            $('#boxcar2_accesstoken').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testBoxcar2-result').html(MEDUSA.config.loading);
            $.get('home/testBoxcar2', {
                accesstoken: boxcar2.accesstoken
            }).done(data => {
                $('#testBoxcar2-result').html(data);
                $('#testBoxcar2').prop('disabled', false);
            });
        }
    }
}
</script>

<style>

</style>
