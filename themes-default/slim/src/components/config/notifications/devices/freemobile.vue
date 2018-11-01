<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
                <span class="icon-notifiers-freemobile" title="Free Mobile"></span>
                <h3><app-link href="http://mobile.free.fr/">Free Mobile</app-link></h3>
                <p>Free Mobile is a famous French cellular network provider.<br> It provides to their customer a free SMS API.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_freemobile" :explanations="['Send SMS notifications?']" @change="save()"/>
                <div v-show="enabled" id="content-use-freemobile-client">

                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="freemobile_notify_onsnatch" :explanations="['send an SMS when a download starts?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="freemobile_notify_ondownload" :explanations="['send an SMS when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="freemobile_notify_onsubtitledownload" :explanations="['send an SMS when subtitles are downloaded?']" @change="save()"/>
                    <config-textbox v-model="id" label="Free Mobile customer ID" id="freemobile_id" :explanations="['It\'s your Free Mobile customer ID (8 digits)']" @change="save()"/>
                    <config-textbox v-model="api" label="Free Mobile API Key" id="freemobile_apikey" :explanations="['Find your API Key in your customer portal.']" @change="save()"/>

                    <div class="testNotification" id="testFreeMobile-result">Click below to test your settings.</div>
                    <input  class="btn-medusa" type="button" value="Test SMS" id="testFreeMobile" @click="test"/>
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'freemobile',
    data: () => ({
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null,
        api: null,
        id: null
    }),
    methods: {
        save() {},
        test() {
            const freemobile = {};
            freemobile.id = $.trim($('#freemobile_id').val());
            freemobile.apikey = $.trim($('#freemobile_apikey').val());
            if (!freemobile.id || !freemobile.apikey) {
                $('#testFreeMobile-result').html('Please fill out the necessary fields above.');
                if (freemobile.id) {
                    $('#freemobile_id').removeClass('warning');
                } else {
                    $('#freemobile_id').addClass('warning');
                }
                if (freemobile.apikey) {
                    $('#freemobile_apikey').removeClass('warning');
                } else {
                    $('#freemobile_apikey').addClass('warning');
                }
                return;
            }
            $('#freemobile_id,#freemobile_apikey').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testFreeMobile-result').html(MEDUSA.config.loading);
            $.get('home/testFreeMobile', {
                freemobile_id: freemobile.id, // eslint-disable-line camelcase
                freemobile_apikey: freemobile.apikey // eslint-disable-line camelcase
            }).done(data => {
                $('#testFreeMobile-result').html(data);
                $('#testFreeMobile').prop('disabled', false);
            });
        }
    }
}
</script>

<style>

</style>
