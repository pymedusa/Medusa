<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-slack" title="Slack"></span>
            <h3><app-link href="https://slack.com">Slack</app-link></h3>
            <p>Slack is a messaging app for teams.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <!-- All form components here for slack client -->
                <config-toggle-slider v-model="enabled" label="Enable" id="use_slack_client" :explanations="['Send slack Home Theater notifications?']" @change="save()"/>
                <div v-show="enabled" id="content-use-slack-client">

                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="slack_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="slack_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="slack_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()"/>
                    <config-textbox v-model="webhook" label="Slack Incoming Webhook" id="slack_webhook" :explanations="['Create an incoming webhook, to communicate with your slack channel.']" @change="save()">
                        <app-link href="https://my.slack.com/services/new/incoming-webhook">https://my.slack.com/services/new/incoming-webhook/</app-link>
                    </config-textbox>

                    <div class="testNotification" id="testSlack-result">Click below to test your settings.</div>
                    <input class="btn-medusa" type="button" value="Test Slack" id="testSlack" @click="test"/>
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'slack',
    data: () => ({
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null,
        webhook: null
    }),
    methods: {
        save() {

        },
        test() {
            const slack = {};
            slack.webhook = $.trim($('#slack_webhook').val());

            if (!slack.webhook) {
                $('#testSlack-result').html('Please fill out the necessary fields above.');
                $('#slack_webhook').addRemoveWarningClass(slack.webhook);
                return;
            }
            $('#slack_webhook').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testSlack-result').html(MEDUSA.config.loading);
            $.get('home/testslack', {
                slack_webhook: slack.webhook // eslint-disable-line camelcase
            }).done(data => {
                $('#testSlack-result').html(data);
                $('#testSlack').prop('disabled', false);
            });
        }
    }
}
</script>

<style>

</style>
