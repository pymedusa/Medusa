<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-plexth" title="Plex Media Client"></span>
            <h3><app-link href="https://plex.tv">Plex Home Theater</app-link></h3>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_plex_client" :explanations="['Send Plex Home Theater notifications?']" @change="save()"/>

                <div v-show="enabled" id="content-use-plex-client">
                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="plex_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="plex_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="plex_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()"/>

                    <config-template label-for="plex_client_host" label="Plex Home Theater IP:Port">
                        <select-list name="plex_client_host" id="plex_client_host" :list-items="host" @change="host = $event.map(x => x.value)"/>
                        <p>one or more hosts running Plex Home Theater<br>(eg. 192.168.1.100:3000, 192.168.1.101:3000)</p>
                    </config-template>

                    <config-textbox v-model="username" label="Username" id="plex_client_username" :explanations="['blank = no authentication']" @change="save()"/>
                    <config-textbox v-model="password" type="password" label="Password" id="plex_client_password" :explanations="['blank = no authentication']" @change="save()"/>

                    <div class="field-pair">
                        <div class="testNotification" id="testPHT-result">Click below to test Plex Home Theater(s)</div>
                        <input class="btn-medusa" type="button" value="Test Plex Home Theater" id="testPHT" @click="test"/>
                        <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                        <div class=clear-left><p>Note: some Plex Home Theaters <b class="boldest">do not</b> support notifications e.g. Plexapp for Samsung TVs</p></div>
                    </div>

                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'plex-client',
    data: () => ({
        host: [],
        username: null,
        password: null,
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null
    }),
    methods: {
        save() {
            this.$emit('update', this.$data);
        },
        test() {
            const plex = {};
            plex.client = {};
            const plexHosts = $.map($('#plex_client_host').find('input'), value => { return value.value }).filter(item => item !== "");
            plex.client.host = plexHosts.join(",");
            plex.client.username = $.trim($('#plex_client_username').val());
            plex.client.password = $.trim($('#plex_client_password').val());
            if (!plex.client.host) {
                $('#testPHT-result').html('Please fill out the necessary fields above.');
                $('#plex_client_host').find('input').addClass('warning');
                return;
            }
            $('#plex_client_host').find('input').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testPHT-result').html(MEDUSA.config.loading);
            $.get('home/testPHT', {
                host: plex.client.host,
                username: plex.client.username,
                password: plex.client.password
            }).done(data => {
                $('#testPHT-result').html(data);
                $('#testPHT').prop('disabled', false);
            });
        }
    }
}
</script>

<style>

</style>
