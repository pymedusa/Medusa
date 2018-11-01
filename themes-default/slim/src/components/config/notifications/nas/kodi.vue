<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-kodi" title="KODI"></span>
            <h3><app-link href="http://kodi.tv">KODI</app-link></h3>
            <p>A free and open source cross-platform media center and home entertainment system software with a 10-foot user interface designed for the living-room TV.</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_kodi" :explanations="['Send KODI commands?']" @change="save()"/>

                <div v-show="enabled" id="content-use-kodi">
                    <config-toggle-slider v-model="alwaysOn" label="Always on" id="kodi_always_on" :explanations="['log errors when unreachable?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSnatch" label="Notify on snatch" id="kodi_notify_onsnatch" :explanations="['send a notification when a download starts?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnDownload" label="Notify on download" id="kodi_notify_ondownload" :explanations="['send a notification when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="notifyOnSubtitleDownload" label="Notify on subtitle download" id="kodi_notify_onsubtitledownload" :explanations="['send a notification when subtitles are downloaded?']" @change="save()"/>
                    <config-toggle-slider v-model="update.library" label="Update library" id="kodi_update_library" :explanations="['update KODI library when a download finishes?']" @change="save()"/>
                    <config-toggle-slider v-model="update.full" label="Full library update" id="kodi_update_full" :explanations="['perform a full library update if update per-show fails?']" @change="save()"/>
                    <config-toggle-slider v-model="cleanLibrary" label="Clean library" id="kodi_clean_library" :explanations="['clean KODI library when replaces a already downloaded episode?']" @change="save()"/>
                    <config-toggle-slider v-model="update.onlyFirst" label="Only update first host" id="kodi_update_onlyfirst" :explanations="['only send library updates/clean to the first active host?']" @change="save()"/>

                    <div class="form-group">
                        <div class="row">
                            <label for="kodi_host" class="col-sm-2 control-label">
                                <span>KODI IP:Port</span>
                            </label>
                            <div class="col-sm-10 content">
                                <select-list name="kodi_host" id="kodi_host" :list-items="host" @change="host = $event.map(x => x.value)"></select-list>
                                <p>host running KODI (eg. 192.168.1.100:8080)</p>
                            </div>
                        </div>
                    </div>

                    <config-textbox v-model="username" label="Username" id="kodi_username" :explanations="['username for your KODI server (blank for none)']" @change="save()"/>
                    <config-textbox v-model="password" type="password" label="Password" id="kodi_password" :explanations="['password for your KODI server (blank for none)']" @change="save()"/>

                    <div class="testNotification" id="testKODI-result">Click below to test.</div>
                    <input class="btn-medusa" type="button" value="Test KODI" id="testKODI" @click="test"/>
                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes"/>

                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'kodi',
    data: () => ({
        enabled: null,
        alwaysOn: null,
        libraryCleanPending: null,
        cleanLibrary: null,
        host: [],
        username: null,
        password: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null,
        update: {
            library: null,
            full: null,
            onlyFirst: null
        }
    }),
    methods: {
        save() {
            this.$emit('update', this.$data);
        },
        test() {
            const kodi = {};
            const kodiHosts = $.map($('#kodi_host').find('input'), value => { return value.value }).filter(item => item !== "");
            kodi.host = kodiHosts.join(",");
            kodi.username = $.trim($('#kodi_username').val());
            kodi.password = $.trim($('#kodi_password').val());
            if (!kodi.host) {
                $('#testKODI-result').html('Please fill out the necessary fields above.');
                $('#kodi_host').find('input').addClass('warning');
                return;
            }
            $('#kodi_host').find('input').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testKODI-result').html(MEDUSA.config.loading);
            $.get('home/testKODI', {
                host: kodi.host,
                username: kodi.username,
                password: kodi.password
            }).done(data => {
                $('#testKODI-result').html(data);
                $('#testKODI').prop('disabled', false);
            });
        }
    }
}
</script>

<style>

</style>
