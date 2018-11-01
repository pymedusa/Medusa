<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-emby" title="Emby"></span>
            <h3><app-link href="http://emby.media">Emby</app-link></h3>
            <p>A home media server built using other popular open source technologies.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <!-- All form components here for emby -->
                <config-toggle-slider v-model="enabled" label="Enable" id="use_emby" :explanations="['Send update commands to Emby?']" @change="save()" ></config-toggle-slider>

                <div v-show="enabled" id="content_use_emby">
                    <config-textbox v-model="host" label="Emby IP:Port" id="emby_host" :explanations="['host running Emby (eg. 192.168.1.100:8096)']" @change="save()" ></config-textbox>
                    <config-textbox v-model="apiKey" label="Api Key" id="emby_apikey" @change="save()" ></config-textbox>

                    <div class="testNotification" id="testEMBY-result">Click below to test.</div>
                    <input class="btn-medusa" type="button" value="Test Emby" id="testEMBY" @click="test"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'emby',
    data: () => ({
        enabled: null,
        host: null,
        apiKey: null
    }),
    methods: {
        save() {
            this.$emit('update', this.$data);
        },
        test() {
            const emby = {};
            emby.host = $('#emby_host').val();
            emby.apikey = $('#emby_apikey').val();
            if (!emby.host || !emby.apikey) {
                $('#testEMBY-result').html('Please fill out the necessary fields above.');
                $('#emby_host').addRemoveWarningClass(emby.host);
                $('#emby_apikey').addRemoveWarningClass(emby.apikey);
                return;
            }
            $('#emby_host,#emby_apikey').children('input').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testEMBY-result').html(MEDUSA.config.loading);
            $.get('home/testEMBY', {
                host: emby.host,
                emby_apikey: emby.apikey // eslint-disable-line camelcase
            }).done(data => {
                $('#testEMBY-result').html(data);
                $('#testEMBY').prop('disabled', false);
            });
        }
    }
}
</script>

<style>

</style>
