<template>
    <div class="row component-group">
        <div class="component-group-desc col-xs-12 col-md-2">
            <span class="icon-notifiers-trakt" title="Trakt"></span>
            <h3><app-link href="https://trakt.tv/">Trakt</app-link></h3>
            <p>trakt helps keep a record of what TV shows and movies you are watching. Based on your favorites, trakt recommends additional shows and movies you'll enjoy!</p>
        </div>
        <div class="col-xs-12 col-md-10">
            <fieldset class="component-group-list">
                <config-toggle-slider v-model="enabled" label="Enable" id="use_trakt" :explanations="['Send Trakt.tv notifications?']" @change="save()"/>
                <div v-show="enabled" id="content-use-trakt-client">

                    <config-textbox v-model="username" label="Username" id="trakt_username" :explanations="['username of your Trakt account.']" @change="save()"/>

                    <config-template label-for="traktPin" label="Trakt PIN">
                        <input type="text" name="trakt_pin" id="trakt_pin" value="" style="display: inline" class="form-control input-sm max-input250" :disabled="accessToken"/>
                        <input type="button" class="btn-medusa" :value="newTokenMessage" id="TraktGetPin" @click="getPin"/>
                        <input type="button" class="btn-medusa hide" value="Authorize Medusa" id="authTrakt" @click="auth"/>
                        <p>PIN code to authorize Medusa to access Trakt on your behalf.</p>
                    </config-template>

                    <config-textbox-number v-model="timeout" label="API Timeout" id="trakt_timeout" :explanations="['Seconds to wait for Trakt API to respond. (Use 0 to wait forever)']"/>

                    <config-template label-for="traktDefaultIndexer" label="Trakt PIN">
                        <select id="trakt_default_indexer" name="trakt_default_indexer" :v-model="defaultIndexer" class="form-control">
                            <option v-for="option in indexersOptions" :key="option.value">
                                {{ option.text }}
                            </option>
                        </select>
                    </config-template id="trakt_default_indexer" label="Default Indexer">

                    <config-toggle-slider v-model="sync" label="Sync libraries" id="trakt_sync" :explanations="
                    ['Sync your Medusa show library with your Trakt collection.',
                    'Note: Don\'t enable this setting if you use the Trakt addon for Kodi or any other script that syncs your library.',
                    'Kodi detects that the episode was deleted and removes from collection which causes Medusa to re-add it. This causes a loop between Medusa and Kodi adding and deleting the episode.']"
                        @change="save()"/>
                    <div v-show="sync" id="content-use-trakt-client">
                            <config-toggle-slider v-model="removeWatchlist" label="Remove Episodes From Collection" id="trakt_remove_watchlist" :explanations="['Remove an Episode from your Trakt Collection if it is not in your Medusa Library.',
                                'Note:Don\'t enable this setting if you use the Trakt addon for Kodi or any other script that syncs your library.']" @change="save()"/>
                    </div>

                    <config-toggle-slider v-model="syncWatchlist" label="Sync watchlist" id="trakt_sync_watchlist" :explanations="
                    ['Sync your Medusa library with your Trakt Watchlist (either Show and Episode).',
                    'Episode will be added on watch list when wanted or snatched and will be removed when downloaded',
                    'Note: By design, Trakt automatically removes episodes and/or shows from watchlist as soon you have watched them.']"
                        @change="save()"/>
                    <div v-show="syncWatchlist" id="content-use-trakt-client">
                        <config-template label-for="trakt_default_indexer" label="Watchlist add method">
                            <select id="trakt_method_add" name="trakt_method_add" v-model="methodAdd" class="form-control">
                                <option v-for="option in traktMethodOptions" :key="option.value">
                                    {{ option.text }}
                                </option>
                            </select>
                            <p>method in which to download episodes for new shows.</p>
                        </config-template>

                        <config-toggle-slider v-model="removeWatchlist" label="Remove episode" id="trakt_remove_watchlist" :explanations="['remove an episode from your watchlist after it\'s downloaded.']" @change="save()"/>
                        <config-toggle-slider v-model="removeSerieslist" label="Remove series" id="trakt_remove_serieslist" :explanations="['remove the whole series from your watchlist after any download.']" @change="save()"/>
                        <config-toggle-slider v-model="removeShowFromApplication" label="Remove watched show" id="trakt_remove_show_from_application" :explanations="['remove the show from Medusa if it\'s ended and completely watched']" @change="save()"/>
                        <config-toggle-slider v-model="startPaused" label="Start paused" id="trakt_start_paused" :explanations="['shows grabbed from your trakt watchlist start paused.']" @change="save()"/>
                    </div>
                    <config-textbox v-model="blacklistName" label="Trakt blackList name" id="trakt_blacklist_name" :explanations="['Name(slug) of List on Trakt for blacklisting show on \'Add Trending Show\' & \'Add Recommended Shows\' pages']" @change="save()"/>

                    <div class="testNotification" id="testTrakt-result">Click below to test.</div>
                    <input type="button" class="btn-medusa" value="Test Trakt" id="testTrakt" @click="test"/>
                    <input type="button" class="btn-medusa" value="Force Sync" id="forceSync" @click="forceSync"/>
                    <input type="hidden" id="trakt_pin_url" :value="pinUrl">
                    <input type="submit" class="btn-medusa config_submitter" value="Save Changes"/>
                </div>
            </fieldset>
        </div>
    </div>
</template>

<script>
export default {
    name: 'trakt',
    data: () => ({
        enabled: null,
        pinUrl: null,
        username: null,
        accessToken: null,
        timeout: null,
        defaultIndexer: null,
        sync: null,
        syncRemove: null,
        syncWatchlist: null,
        methodAdd: null,
        removeWatchlist: null,
        removeSerieslist: null,
        removeShowFromApplication: null,
        startPaused: null,
        blacklistName: null,
        traktMethodOptions: [
            { text: 'Skip all', value: 0 },
            { text: 'Download pilot only', value: 1 },
            { text: 'Get whole show', value: 2 }
        ],
    }),
    computed: {
        newTokenMessage() {
            const { accessToken } =  this;
            return 'Get ' + accessToken ? 'New ' : ' ' + 'Trakt PIN'
        },
        indexersOptions() {
            if (!this.configLoaded) {
                return;
            }
            const { traktIndexers } = this.config.indexers.config.main;
            const { indexers } = this.config.indexers.config;
            let options = [];
            const validTraktIndexer = Object.keys(indexers).filter(k => traktIndexers[k])
            return validTraktIndexer.map(indexer => {
                return { text: indexer, value: indexers[indexer].id }
            })
        }
    },
    mounted() {
        // TODO: vueify this.
        $('#trakt_pin').on('keyup change', () => {
            if ($('#trakt_pin').val().length === 0) {
                $('#TraktGetPin').removeClass('hide');
                $('#authTrakt').addClass('hide');
            } else {
                $('#TraktGetPin').addClass('hide');
                $('#authTrakt').removeClass('hide');
            }
        });
    },
    methods: {
        getPin() {
            window.open($('#trakt_pin_url').val(), 'popUp', 'toolbar=no, scrollbars=no, resizable=no, top=200, left=200, width=650, height=550');
            $('#trakt_pin').prop('disabled', false);
        },
        auth() {
            const trakt = {};
            trakt.pin = $('#trakt_pin').val();
            if (trakt.pin.length !== 0) {
                $.get('home/getTraktToken', {
                    trakt_pin: trakt.pin // eslint-disable-line camelcase
                }).done(data => {
                    $('#testTrakt-result').html(data);
                    $('#authTrakt').addClass('hide');
                    $('#trakt_pin').prop('disabled', true);
                    $('#trakt_pin').val('');
                    $('#TraktGetPin').removeClass('hide');
                });
            }
        },
        test() {
            const trakt = {};
            trakt.username = $.trim($('#trakt_username').val());
            trakt.trendingBlacklist = $.trim($('#trakt_blacklist_name').val());
            if (!trakt.username) {
                $('#testTrakt-result').html('Please fill out the necessary fields above.');
                $('#trakt_username').addRemoveWarningClass(trakt.username);
                return;
            }

            if (/\s/g.test(trakt.trendingBlacklist)) {
                $('#testTrakt-result').html('Check blacklist name; the value needs to be a trakt slug');
                $('#trakt_blacklist_name').addClass('warning');
                return;
            }
            $('#trakt_username').removeClass('warning');
            $('#trakt_blacklist_name').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testTrakt-result').html(MEDUSA.config.loading);
            $.get('home/testTrakt', {
                username: trakt.username,
                blacklist_name: trakt.trendingBlacklist // eslint-disable-line camelcase
            }).done(data => {
                $('#testTrakt-result').html(data);
                $('#testTrakt').prop('disabled', false);
            });
        },
        forceSync() {
            $('#testTrakt-result').html(MEDUSA.config.loading);
            $.getJSON('home/forceTraktSync', data => {
                $('#testTrakt-result').html(data.result);
            });
        }
    }
}
</script>

<style>

</style>
