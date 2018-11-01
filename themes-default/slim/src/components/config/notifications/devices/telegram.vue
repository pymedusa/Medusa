<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-telegram" title="Telegram"></span>
            <h3><app-link href="https://telegram.org/">Telegram</app-link></h3>
            <p>Telegram is a cloud-based instant messaging service.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_telegram" :explanations="['Send Telegram notifications?']" @change="save()"/>
                <div v-show="enabled" id="content-use-telegram-client">
                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="telegram_notify_onsnatch" :explanations="['Send a message when a download starts??']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="telegram_notify_ondownload" :explanations="['send a message when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="telegram_notify_onsubtitledownload" :explanations="['send a message when subtitles are downloaded?']" @change="save()"/>
                    <config-textbox v-model="id" label="User/group ID" id="telegram_id" :explanations="['Contact @myidbot on Telegram to get an ID']" @change="save()"/>
                    <config-textbox v-model="api" label="Bot API token" id="telegram_apikey" :explanations="['Contact @BotFather on Telegram to set up one']" @change="save()"/>

                    <div class="testNotification" id="testTelegram-result">Click below to test your settings.</div>
                    <input  class="btn-medusa" type="button" value="Test Telegram" id="testTelegram" @click="test"/>
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'telegram',
    data: () => ({
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null,
        api: null,
        id: null
    }),
    methods: {
        save() {

        },
        test() {
            const telegram = {};
            telegram.id = $.trim($('#telegram_id').val());
            telegram.apikey = $.trim($('#telegram_apikey').val());
            if (!telegram.id || !telegram.apikey) {
                $('#testTelegram-result').html('Please fill out the necessary fields above.');
                $('#telegram_id').addRemoveWarningClass(telegram.id);
                $('#telegram_apikey').addRemoveWarningClass(telegram.apikey);
                return;
            }
            $('#telegram_id,#telegram_apikey').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testTelegram-result').html(MEDUSA.config.loading);
            $.get('home/testTelegram', {
                telegram_id: telegram.id, // eslint-disable-line camelcase
                telegram_apikey: telegram.apikey // eslint-disable-line camelcase
            }).done(data => {
                $('#testTelegram-result').html(data);
                $('#testTelegram').prop('disabled', false);
            });
        }
    }
}
</script>

<style>

</style>
