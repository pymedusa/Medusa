<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-twitter" title="Twitter"></span>
            <h3><app-link href="https://www.twitter.com">Twitter</app-link></h3>
            <p>A social networking and microblogging service, enabling its users to send and read other users' messages called tweets.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_twitter" :explanations="['Should Medusa post tweets on Twitter?', 'Note: you may want to use a secondary account.']" @change="save()"/>
                <div v-show="enabled" id="content-use-twitter">
                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="twitter_notify_onsnatch" :explanations="['send an SMS when a download starts?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="twitter_notify_ondownload" :explanations="['send an SMS when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="twitter_notify_onsubtitledownload" :explanations="['send an SMS when subtitles are downloaded?']" @change="save()"/>
                    <config-toggle-slider v-model="directMessage" label="Send direct message" id="twitter_usedm" :explanations="['send a notification via Direct Message, not via status update']" @change="save()"/>

                    <config-textbox v-model="dmto" label="Send DM to" id="twitter_dmto" :explanations="['Twitter account to send Direct Messages to (must follow you)']" @change="save()"/>

                    <config-template label-for="twitterStep1" label="Step 1">
                        <span style="font-size: 11px;">Click the "Request Authorization" button. <br>This will open a new page containing an auth key. <br>Note: if nothing happens check your popup blocker.</span>
                        <p><input class="btn-medusa" type="button" value="Request Authorization" id="twitter-step-1" @click="twitterStep1($event)"/></p>
                    </config-template>

                    <config-template label-for="twitterStep2" label="Step 2">
                        <input type="text" id="twitter_key" v-model="twitterKey" class="form-control input-sm max-input350" style="display: inline" placeholder="Enter the key Twitter gave you, and click 'Verify Key'"/>
                        <input class="btn-medusa btn-inline" type="button" value="Verify Key" id="twitter-step-2" @click="twitterStep2($event)"/>
                    </config-template>

                    <div class="testNotification" id="testTwitter-result" v-html="twitterTestInfo"></div>
                    <input  class="btn-medusa" type="button" value="Test Twitter" id="testTwitter" @click="test" />
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'twitter',
    data: () => ({
        twitterTestInfo: 'Click below to test.',
        twitterKey: '',
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null,
        dmto: null,
        username: null,
        password: null,
        prefix: null,
        directMessage: null
    }),
    methods: {
        twitterStep1() {
            this.twitterTestInfo = MEDUSA.config.loading;

            apiRoute('home/twitterStep1').then(({ data }) => {
                this.twitterTestInfo = '<b>Step1:</b> Confirm Authorization';
                window.open(data);
            });
        },
        twitterStep2() {
            const twitter = {};
            const { twitterKey } = this;
            twitter.key = twitterKey;

            if (!twitter.key) {
                this.twitterTestInfo = 'Please fill out the necessary fields above.';
                return;
            }

            apiRoute('home/twitterStep2', { params: { key: twitter.key } }).then(({ data }) => {
                this.twitterTestInfo = data;
            }).catch(error => {
                this.twitterTestInfo = error;
            });
        },
        test() {
            apiRoute('home/testTwitter').then(({ data }) => {
                this.twitterTestInfo = data;
            }).catch(error => {
                this.twitterTestInfo = 'Error while trying to request for a test on the twitter api.'
            });
        }
    }
}
</script>

<style>

</style>
