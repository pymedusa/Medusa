<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-plex" title="Plex Media Server"></span>
            <h3><app-link href="https://plex.tv">Plex Media Server</app-link></h3>
            <p>Experience your media on a visually stunning, easy to use interface on your Mac connected to your TV. Your media library has never looked this good!</p>
            <p v-if="enabled" class="plexinfo">For sending notifications to Plex Home Theater (PHT) clients, use the KODI notifier with port <b>3005</b>.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_plex_server" :explanations="['Send KODI commands?']" @change="save()"/>

                <div v-show="enabled" id="content-use-plex-server">
                    <config-textbox v-model="token" label="Plex Media Server Auth Token" id="plex_server_token" @change="save()" >
                        <p>Auth Token used by plex</p>
                        <p><span>See: <app-link href="https://support.plex.tv/hc/en-us/articles/204059436-Finding-your-account-token-X-Plex-Token" class="wiki"><strong>Finding your account token</strong></app-link></span></p>
                    </config-textbox>

                    <config-textbox v-model="username" label="Username" id="plex_server_username" :explanations="['blank = no authentication']" @change="save()"/>
                    <config-textbox v-model="password" type="password" label="Password" id="plex_server_password" :explanations="['blank = no authentication']" @change="save()"/>

                    <config-toggle-slider v-model="updateLibrary" label="Update Library" id="plex_update_library" :explanations="['log errors when unreachable?']" @change="save()"/>

                    <config-template label-for="plex_server_host" label="Plex Media Server IP:Port">
                        <select-list name="plex_server_host" id="plex_server_host" :list-items="host" @change="host = $event.map(x => x.value)"/>
                        <p>one or more hosts running Plex Media Server<br>(eg. 192.168.1.1:32400, 192.168.1.2:32400)</p>
                    </config-template>

                    <config-toggle-slider v-model="https" label="HTTPS" id="plex_server_https" :explanations="['use https for plex media server requests?']" @change="save()"/>

                    <div class="field-pair">
                        <div class="testNotification" id="testPMS-result">Click below to test Plex Media Server(s)</div>
                        <input class="btn-medusa" type="button" value="Test Plex Media Server" id="testPMS" @click="test"/>
                        <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>
                        <div class="clear-left">&nbsp;</div>
                    </div>

                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'plex-server',
    data: () => ({
        updateLibrary: null,
        host: [],
        enabled: null,
        https: null,
        username: null,
        password: null,
        token: null
    }),
     methods: {
        save() {
            this.$emit('update', this.$data);
        },
        test() {
            const plex = {};
            plex.server = {};
            const plexHosts = $.map($('#plex_server_host').find('input'), value => { return value.value }).filter(item => item !== "");
            plex.server.host = plexHosts.join(",");

            plex.server.username = $.trim($('#plex_server_username').val());
            plex.server.password = $.trim($('#plex_server_password').val());
            plex.server.token = $.trim($('#plex_server_token').val());
            if (!plex.server.host) {
                $('#testPMS-result').html('Please fill out the necessary fields above.');
                $('#plex_server_host').find('input').addClass('warning');
                return;
            }
            $('#plex_server_host').find('input').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testPMS-result').html(MEDUSA.config.loading);
            $.get('home/testPMS', {
                host: plex.server.host,
                username: plex.server.username,
                password: plex.server.password,
                plex_server_token: plex.server.token // eslint-disable-line camelcase
            }).done(data => {
                $('#testPMS-result').html(data);
                $('#testPMS').prop('disabled', false);
            });
        }
     }
}
</script>

<style>

</style>
