<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-pushover" title="Pushover"></span>
            <h3><app-link href="https://pushover.net/">Pushover</app-link></h3>
            <p>Pushover makes it easy to send real-time notifications to your Android and iOS devices.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <!-- All form components here for pushover -->
                <config-toggle-slider v-model="enabled" label="Enable" id="use_pushover_client" :explanations="['Send Pushover notifications?']" @change="save()"/>
                <div v-show="enabled" id="content-use-pushover">
                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="pushover_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="pushover_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="pushover_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()"/>

                    <config-textbox v-model="userKey" label="Pushover Key" id="pushover_userkey" :explanations="['user key of your Pushover account']" @change="save()"/>

                    <config-textbox v-model="apiKey" label="Pushover API key" id="pushover_apikey" @change="save()" >
                        <span><app-link href="https://pushover.net/apps/build/"><b>Click here</b></app-link> to create a Pushover API key</span>
                    </config-textbox>

                    <config-template label-for="pushover_device" label="Pushover Devices">
                        <select-list name="pushover_device" id="pushover_device" :list-items="device" @change="device = $event.map(x => x.value)"/>
                        <p>List of pushover devices you want to send notifications to</p>
                    </config-template>

                    <config-template label-for="pushover_spound" label="Pushover notification sound">
                        <select id="pushover_sound" name="pushover_sound" v-model="sound" class="form-control">
                            <option v-for="option in pushoverSoundOptions" :v-model="option.value" :key="option.value">
                                {{ option.text }}
                            </option>
                        </select>
                        <span>Choose notification sound to use</span>
                    </config-template>

                    <div class="testNotification" id="testPushover-result">Click below to test.</div>
                    <input  class="btn-medusa" type="button" value="Test Pushover" id="testPushover" @click="test"/>
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'pushover',
    data: () => ({
        enabled: null,
        apiKey: null,
        userKey: null,
        device: [],
        sound: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null,
        pushoverSoundOptions: [
            { text: 'Pushover', value: 'pushover' },
            { text: 'Bike', value: 'bike' },
            { text: 'Bugle', value: 'bugle' },
            { text: 'Cash Register', value: 'cashregister' },
            { text: 'classical', value: 'classical' },
            { text: 'Cosmic', value: 'cosmic' },
            { text: 'Falling', value: 'falling' },
            { text: 'Gamelan', value: 'gamelan' },
            { text: 'Incoming', value: 'incoming' },
            { text: 'Intermission', value: 'intermission' },
            { text: 'Magic', value: 'magic' },
            { text: 'Mechanical', value: 'mechanical' },
            { text: 'Piano Bar', value: 'pianobar' },
            { text: 'Siren', value: 'siren' },
            { text: 'Space Alarm', value: 'spacealarm' },
            { text: 'Tug Boat', value: 'tugboat' },
            { text: 'Alien Alarm (long)', value: 'alien' },
            { text: 'Climb (long)', value: 'climb' },
            { text: 'Persistent (long)', value: 'persistant' },
            { text: 'Pushover Echo (long)', value: 'echo' },
            { text: 'Up Down (long)', value: 'updown' },
            { text: 'None (silent)', value: 'none' },
            { text: 'Device specific', value: 'default' }
        ],
    }),
    methods: {
        save() {},
        test() {
            const pushover = {};
            pushover.userkey = $('#pushover_userkey').val();
            pushover.apikey = $('#pushover_apikey').val();
            if (!pushover.userkey || !pushover.apikey) {
                $('#testPushover-result').html('Please fill out the necessary fields above.');
                $('#pushover_userkey').addRemoveWarningClass(pushover.userkey);
                $('#pushover_apikey').addRemoveWarningClass(pushover.apikey);
                return;
            }
            $('#pushover_userkey,#pushover_apikey').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testPushover-result').html(MEDUSA.config.loading);
            $.get('home/testPushover', {
                userKey: pushover.userkey,
                apiKey: pushover.apikey
            }).done(data => {
                $('#testPushover-result').html(data);
                $('#testPushover').prop('disabled', false);
            });
        }
    }
}
</script>

<style>

</style>
