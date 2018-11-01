<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-nmj" title="Networked Media Jukebox v2"></span>
            <h3><app-link href="http://www.popcornhour.com/">NMJv2</app-link></h3>
            <p>The Networked Media Jukebox, or NMJv2, is the official media jukebox interface made available for the Popcorn Hour 300 & 400-series.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_nmjv2" :explanations="['Send popcorn hour (nmjv2) notifications?']" @change="save()"/>
                <div v-show="enabled" id="content-use-nmjv2">

                    <config-textbox v-model="host" label="Popcorn IP address" id="nmjv2_host" :explanations="['IP address of Popcorn 300/400-series (eg. 192.168.1.100)']" @change="save()"/>

                    <config-template label-for="nmjv2_database_location" label="Database location">
                        <label for="NMJV2_DBLOC_A" class="space-right">
                            <input type="radio" name="nmjv2_dbloc" id="NMJV2_DBLOC_A" v-model="dbloc"/>
                            PCH Local Media
                        </label>
                        <label for="NMJV2_DBLOC_B">
                            <input type="radio" name="nmjv2_dbloc" id="NMJV2_DBLOC_B" v-model="dbloc"/>
                            PCH Network Media
                        </label>
                    </config-template>

                    <config-template label-for="nmjv2_database_instance" label="Database instance">
                        <select id="NMJv2db_instance" class="form-control input-sm">
                            <option value="0">#1 </option>
                            <option value="1">#2 </option>
                            <option value="2">#3 </option>
                            <option value="3">#4 </option>
                            <option value="4">#5 </option>
                            <option value="5">#6 </option>
                            <option value="6">#7 </option>
                        </select>
                        <span>adjust this value if the wrong database is selected.</span>
                    </config-template>

                    <config-template label-for="get_nmjv2_find_database" label="Find database">
                        <input type="button" class="btn-medusa btn-inline" value="Find Database" id="settingsNMJv2" @click="settings"/>
                        <span>the Popcorn Hour device must be powered on.</span>
                    </config-template>

                    <config-textbox v-model="database" label="NMJv2 database" id="nmjv2_database" :explanations="['automatically filled via the \'Find Database\' buttons.']" @change="save()"/>
                    <div class="testNotification" id="testNMJv2-result">Click below to test.</div>
                    <input class="btn-medusa" type="button" value="Test NMJv2" id="testNMJv2" @click="test"/>
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'nmjv2',
    data: () => ({
        enabled: null,
        host: null,
        dbloc: null,
        database: null
    }),
    methods: {
        settings() {
            const nmjv2 = {};
            nmjv2.host = $('#nmjv2_host').val();
            if (nmjv2.host) {
                $('#testNMJv2-result').html(MEDUSA.config.loading);
                nmjv2.dbloc = '';
                const radios = document.getElementsByName('nmjv2_dbloc');
                for (let i = 0, len = radios.length; i < len; i++) {
                    if (radios[i].checked) {
                        nmjv2.dbloc = radios[i].value;
                        break;
                    }
                }

                nmjv2.dbinstance = $('#NMJv2db_instance').val();
                $.get('home/settingsNMJv2', {
                    host: nmjv2.host,
                    dbloc: nmjv2.dbloc,
                    instance: nmjv2.dbinstance
                }, data => {
                    if (data === null) {
                        $('#nmjv2_database').removeAttr('readonly');
                    }
                    const JSONData = $.parseJSON(data);
                    $('#testNMJv2-result').html(JSONData.message);
                    $('#nmjv2_database').val(JSONData.database);

                    if (JSONData.database) {
                        $('#nmjv2_database').prop('readonly', true);
                    } else {
                        $('#nmjv2_database').removeAttr('readonly');
                    }
                });
            } else {
                alert('Please fill in the Popcorn IP address'); // eslint-disable-line no-alert
                $('#nmjv2_host').focus();
            }
        },
        test() {
            const nmjv2 = {};
            nmjv2.host = $.trim($('#nmjv2_host').val());
            if (nmjv2.host) {
                $('#nmjv2_host').removeClass('warning');
                $(this).prop('disabled', true);
                $('#testNMJv2-result').html(MEDUSA.config.loading);
                $.get('home/testNMJv2', {
                    host: nmjv2.host
                }).done(data => {
                    $('#testNMJv2-result').html(data);
                    $('#testNMJv2').prop('disabled', false);
                });
            } else {
                $('#testNMJv2-result').html('Please fill out the necessary fields above.');
                $('#nmjv2_host').addClass('warning');
            }
        }
    }
}
</script>

<style>

</style>
