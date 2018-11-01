<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-pushbullet" title="Pushbullet"></span>
            <h3><app-link href="https://www.pushbullet.com">Pushbullet</app-link></h3>
            <p>Pushbullet is a platform for receiving custom push notifications to connected devices running Android and desktop Chrome browsers.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_pushbullet" :explanations="['Send pushbullet notifications?']" @change="save()"/>
                <div v-show="enabled" id="content-use-pushbullet-client">

                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="pushbullet_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="pushbullet_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="pushbullet_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()"/>
                    <config-textbox v-model="api" label="Pushbullet API key" id="pushbullet_api" :explanations="['API key of your Pushbullet account.']" @change="save()"/>

                    <config-template label-for="pushbullet_device_list" label="Pushbullet devices">
                        <input type="button" class="btn-medusa btn-inline" value="Update device list" id="get-pushbullet-devices" @click="getDeviceOptions" />
                        <select id="pushbullet_device_list" name="pushbullet_device_list" :v-model="device" class="form-control">
                            <option v-for="option in deviceOptions" :v-model="option.value" :key="option.value" @change="testInfo = 'Don\'t forget to save your new pushbullet settings.'">
                                {{ option.text }}
                            </option>
                        </select>
                        <span>select device you wish to push to.</span>
                    </config-template>

                    <div class="testNotification" id="testPushbullet-resultsfsf">{{ testInfo }}</div>
                    <input type="button" class="btn-medusa" value="Test Pushbullet" id="testPushbullet" @click="test" />
                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'pushbullet',
    data: () => ({
        api: '',
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null,
        authToken: null,
        device: null,
        deviceOptions: [
            { text: 'All devices', value: '' }
        ],
        testInfo: 'Click below to test.'
    }),
    methods: {
        save() {},
        getDeviceOptions() {
            const { api } = this;
            if (!api) {
                this.testInfo = `You didn't supply a Pushbullet api key`;
                $('#pushbullet_api').find('input').focus();
                return false;
            }

            apiRoute('home/getPushbulletDevices', { params: { api }}).then(({ data }) => {
                let options = [];

                if (!data) {
                    return false;
                }

                options.push({text: 'All devices', value: ''});
                for (device of data.devices) {
                    if (device.active === true) {
                        options.push({
                            text: device.nickname,
                            value: device.iden
                        });
                    }
                }
                this.pushbulletDeviceOptions = options;
                this.testInfo = 'Device list updated. Please choose a device to push to.';
            });
        },
        test() {
            const { api } = this;
            if (!api) {
                this.testInfo = `You didn't supply a Pushbullet API key`;
                $('#pushbullet_api').find('input').focus();
                return false;
            }

            apiRoute('home/testPushbullet', { params: { api }}).then(({ data }) => {
                this.testInfo = data;
            });
        },
    }
}
</script>

<style>

</style>
