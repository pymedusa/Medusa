<template>
    <div id="config-content">
        <form id="configForm" method="post" @submit.prevent="save()">
            <div id="config-components">
                <ul>
                    <li><app-link href="#home-theater-nas">Home Theater / NAS</app-link></li>
                    <li><app-link href="#devices">Devices</app-link></li>
                    <li><app-link href="#social">Social</app-link></li>
                </ul>

                <div id="home-theater-nas">
                    <component v-for="component in components.nas" :is="component" :key="component" @update="save"/>
                </div>

                <div id="devices">
                    <component v-for="component in components.devices" :is="component" :key="component" @update="save"/>
                </div>

                <div id="social">
                    <component v-for="component in components.social" :is="component" :key="component" @update="save"/>
                </div>
                <br><input type="submit" class="config_submitter btn-medusa" value="Save Changes"/><br>
            </div>
        </form>
    </div>
</template>

<script>
import * as Devices from './devices';
import * as Nas from './nas';
import * as Social from './social';

export default {
    name: 'config-notifications',
    components: {
        ...Devices,
        ...Nas,
        ...Social
    },
    data() {
        return {
            components: {
                nas: [
                    'kodi',
                    'plex-server',
                    'plex-client',
                    'emby',
                    'nmj',
                    'nmjv2',
                    'synology',
                    'synology-indexer',
                    'py-tivo'
                ],
                devices: [
                    'growl',
                    'prowl',
                    'libnotify',
                    'pushover',
                    'boxcar2',
                    'pushalot',
                    'pushbullet',
                    'freemobile',
                    'telegram'
                ],
                social: [
                    'twitter',
                    'trakt',
                    'email',
                    'slack'
                ]
            },
            configLoaded: false
        };
    },
    computed: {
        stateNotifiers() {
            return this.$store.state.notifiers;
        }
    },
    created() {
        const { $store } = this;
        // Needed for the show-selector component
        $store.dispatch('getShows');
    },
    mounted() {
        $('#config-content').tabs();

        // The real vue stuff
        // This is used to wait for the config to be loaded by the store.
        this.$once('loaded', () => {
            this.configLoaded = true;
        });
    },
    methods: {
        save(config) {
            const { $store } = this;

            // We want to wait until the page has been fully loaded, before starting to save stuff.
            if (!this.configLoaded) {
                return;
            }
            // Disable the save button until we're done.
            this.saving = true;

            const section = 'main';

            $store.dispatch('setConfig', { section, config }).then(() => {
                this.$snotify.success(
                    'Saved Notifiers config',
                    'Saved',
                    { timeout: 5000 }
                );
            }).catch(() => {
                this.$snotify.error(
                    'Error while trying to save notifiers config',
                    'Error'
                );
            });
        }
    }
}
</script>

<style>

</style>
