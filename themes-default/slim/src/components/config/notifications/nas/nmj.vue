<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-nmj" title="Networked Media Jukebox"></span>
            <h3><app-link href="http://www.popcornhour.com/">NMJ</app-link></h3>
            <p>The Networked Media Jukebox, or NMJ, is the official media jukebox interface made available for the Popcorn Hour 200-series.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <!-- All form components here for nmj -->
                <config-toggle-slider v-model="enabled" label="Enable" id="use_nmj" :explanations="['Send update commands to NMJ?']" @change="save()"/>
                <div v-show="enabled" id="content-use-nmj">
                    <config-textbox v-model="host" label="Popcorn IP address" id="nmj_host" :explanations="['IP address of Popcorn 200-series (eg. 192.168.1.100)']" @change="save()"/>

                    <config-template label-for="settingsNMJ" label="Get settings">
                        <input class="btn-medusa btn-inline" type="button" value="Get Settings" id="settingsNMJ" @click="settings"/>
                        <span>the Popcorn Hour device must be powered on and NMJ running.</span>
                    </config-template>

                    <config-textbox v-model="database" label="NMJ database" id="nmj_database" :explanations="['automatically filled via the \'Get Settings\' button.']" @change="save()"/>

                    <config-textbox v-model="mount" label="NMJ mount" id="nmj_mount" :explanations="['automatically filled via the \'Get Settings\' button.']" @change="save()"/>

                    <div class="testNotification" id="testNMJ-result">Click below to test.</div>
                    <input class="btn-medusa" type="button" value="Test NMJ" id="testNMJ" @click="test"/>
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>

                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'nmj',
    data: () => ({
        enabled: null,
        host: null,
        database: null,
        mount: null
    }),
    methods: {
        settings() {
            const nmj = {};
            nmj.host = $('#nmj_host').val();
            if (nmj.host) {
                $('#testNMJ-result').html(MEDUSA.config.loading);
                $.get('home/settingsNMJ', {
                    host: nmj.host
                }, data => {
                    if (data === null) {
                        $('#nmj_database').removeAttr('readonly');
                        $('#nmj_mount').removeAttr('readonly');
                    }
                    const JSONData = $.parseJSON(data);
                    $('#testNMJ-result').html(JSONData.message);
                    $('#nmj_database').val(JSONData.database);
                    $('#nmj_mount').val(JSONData.mount);

                    if (JSONData.database) {
                        $('#nmj_database').prop('readonly', true);
                    } else {
                        $('#nmj_database').removeAttr('readonly');
                    }
                    if (JSONData.mount) {
                        $('#nmj_mount').prop('readonly', true);
                    } else {
                        $('#nmj_mount').removeAttr('readonly');
                    }
                });
            } else {
                alert('Please fill in the Popcorn IP address'); // eslint-disable-line no-alert
                $('#nmj_host').focus();
            }
        },
        test() {
            const nmj = {};
            nmj.host = $.trim($('#nmj_host').val());
            nmj.database = $('#nmj_database').val();
            nmj.mount = $('#nmj_mount').val();
            if (nmj.host) {
                $('#nmj_host').removeClass('warning');
                $(this).prop('disabled', true);
                $('#testNMJ-result').html(MEDUSA.config.loading);
                $.get('home/testNMJ', {
                    host: nmj.host,
                    database: nmj.database,
                    mount: nmj.mount
                }).done(data => {
                    $('#testNMJ-result').html(data);
                    $('#testNMJ').prop('disabled', false);
                });
            } else {
                $('#testNMJ-result').html('Please fill out the necessary fields above.');
                $('#nmj_host').addClass('warning');
            }
        }
    }
}
</script>

<style>

</style>
