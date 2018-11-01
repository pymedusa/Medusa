<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-prowl" title="Prowl"></span>
            <h3><app-link href="http://www.prowlapp.com/">Prowl</app-link></h3>
            <p>A Growl client for iOS.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_prowl" :explanations="['Send Prowl notifications?']" @change="save()"/>
                <div v-show="enabled" id="content-use-prowl">
                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="prowl_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="prowl_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="prowl_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()"/>
                    <config-textbox v-model="messageTitle" label="Prowl Message Title" id="prowl_message_title" @change="save()"/>

                    <config-template label-for="prowl_api" label="Api">
                        <select-list name="prowl_api" id="prowl_api" csv-enabled :list-items="api" @change="onChangeProwlApi"/>
                        <span>Prowl API(s) listed here, will receive notifications for <b>all</b> shows.
                            Your Prowl API key is available at:
                            <app-link href="https://www.prowlapp.com/api_settings.php">
                            https://www.prowlapp.com/api_settings.php</app-link><br>
                            (This field may be blank except when testing.)
                        </span>
                    </config-template>

                    <config-template label-for="prowl_show_notification_list" label="Show notification list">
                        <show-selector select-class="form-control input-sm max-input350" placeholder="-- Select a Show --" @change="updateApiKeys($event)"/>
                    </config-template>

                    <div class="form-group">
                        <div class="row">
                            <!-- bs3 and 4 -->
                            <div class="offset-sm-2 col-sm-offset-2 col-sm-10 content">
                                <select-list name="prowl-show-list" id="prowl-show-list" :list-items="selectedShowApiKeys" @change="savePerShowNotifyList('prowl')"/>
                                Configure per-show notifications here by entering Prowl API key(s), after selecting a show in the drop-down box.
                                Be sure to activate the \'Save for this show\' button below after each entry.
                            </div>
                        </div>
                    </div>

                    <config-template label-for="prowl-show-save-button" label="">
                        <input id="prowl-show-save-button" class="btn-medusa" type="button" value="Save for this show" @click="savePerShowNotifyList('prowl')"/>
                    </config-template>

                    <config-template label-for="prowl_priority" label="Prowl priority">
                        <select id="prowl_priority" name="prowl_priority" :v-model="priority" class="form-control input-sm">
                            <option v-for="option in priorityOptions" :v-model="option.value" :key="option.value">
                                {{ option.text }}
                            </option>
                        </select>
                        <span>priority of Prowl messages from Medusa.</span>
                    </config-template>

                    <div class="testNotification" id="testProwl-result">Click below to test.</div>
                    <input class="btn-medusa" type="button" value="Test Prowl" id="testProwl" @click="test"/>
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'prowl',
    data: () => ({
        enabled: null,
        api: [],
        messageTitle: null,
        priority: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null,
        selectedShow: null,
        selectedShowApiKeys: [],
        priorityOptions: [
            { text: 'Very Low', value: -2 },
            { text: 'Moderate', value: -1 },
            { text: 'Normal', value: 0 },
            { text: 'High', value: 1 },
            { text: 'Emergency', value: 2 }
        ],
    }),
    methods: {
        save() {

        },
        test() {
            const prowl = {};
            prowl.api = $.trim($('#prowl_api').find('input').val());
            prowl.priority = $('#prowl_priority').find('input').val();
            if (!prowl.api) {
                $('#testProwl-result').html('Please fill out the necessary fields above.');
                $('#prowl_api').find('input').addClass('warning');
                return;
            }
            $('#prowl_api').find('input').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testProwl-result').html(MEDUSA.config.loading);
            $.get('home/testProwl', {
                prowl_api: prowl.api, // eslint-disable-line camelcase
                prowl_priority: prowl.priority // eslint-disable-line camelcase
            }).done(data => {
                $('#testProwl-result').html(data);
                $('#testProwl').prop('disabled', false);
            });
        },
        onChangeProwlApi(items) {
            this.api = items.map(item => item.value);
        },
        prowlUpdateApiKeys(selectedShow) {
            this.prowlSelectedShow = selectedShow;
            apiRoute('home/loadShowNotifyLists').then(({ data }) => {
                if (data._size > 0) {
                    const list = data[selectedShow].prowl_notify_list ? data[selectedShow].prowl_notify_list.split(',') : [];
                    this.prowlSelectedShowApiKeys = selectedShow ? list : [];
                }
            });
        },
        savePerShowNotifyList() {
            const {
                prowlSelectedShow,
                prowlSelectedShowApiKeys,
                prowlUpdateApiKeys
            } = this;

            let form = new FormData();
            let reloadList = prowlUpdateApiKeys;
            form.set('show', prowlSelectedShow);
            form.set('prowlAPIs', prowlSelectedShowApiKeys);

            // Save the list
            apiRoute.post('home/saveShowNotifyList', form);
        }
    }
}
</script>

<style>

</style>
