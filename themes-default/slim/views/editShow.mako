<%inherit file="/layouts/main.mako"/>
<link rel="stylesheet" type="text/css" href="css/vue/editshow.css?${sbPID}" />
<%block name="scripts">
<%include file="/vue-components/select-list-ui.mako"/>
<%include file="/vue-components/anidb-release-group-ui.mako"/>
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        metaInfo: {
            title: 'Edit Show'
        },
        data() {
            return {
                seriesSlug: $('#series-slug').attr('value'),
                seriesId: $('#series-id').attr('value'),
                indexerName: $('#indexer-name').attr('value'),
                config: MEDUSA.config,
                series: {
                    config: {
                        aliases: [],
                        dvdOrder: false,
                        defaultEpisodeStatus: '',
                        seasonFolders: true,
                        anime: false,
                        scene: false,
                        sports: false,
                        paused: false,
                        location: '',
                        airByDate: false,
                        subtitlesEnabled: false,
                        release: {
                            requiredWords: [],
                            ignoredWords: [],
                            blacklist: [],
                            whitelist: [],
                            allgroups: []
                        },
                        qualities: {
                            preferred: [],
                            allowed: []
                        }
                    },
                    language: 'en'
                },
                defaultEpisodeStatusOptions: [
                    {text: 'Wanted', value: 'Wanted'},
                    {text: 'Skipped', value: 'Skipped'},
                    {text: 'Ignored', value: 'Ignored'}
                ],
                seriesLoaded: false,
                saving: false
            }
        },
        async mounted() {
            const seriesSlug = $('#series-slug').attr('value');
            const url = 'series/' + seriesSlug;
            try {
                const response = await api.get('series/' + this.seriesSlug);
                this.series = Object.assign({}, this.series, response.data);
                this.series.language = response.data.language;
            } catch (error) {
                console.debug('Could not get series info for: '+ seriesSlug);
            }
            this.seriesLoaded = true;
        },
        methods: {
            async saveSeries(subject) {
                // We want to wait until the page has been fully loaded, before starting to save stuff.
                if (!this.seriesLoaded) {
                    return;
                }

                // Disable the save button until we're done.
                this.saving = true;

                if (['series', 'all'].includes(subject)) {
                    const data = {
                        config: {
                            aliases: this.series.config.aliases,
                            defaultEpisodeStatus: this.series.config.defaultEpisodeStatus,
                            dvdOrder: this.series.config.dvdOrder,
                            seasonFolders: this.series.config.seasonFolders,
                            anime: this.series.config.anime,
                            scene: this.series.config.scene,
                            sports: this.series.config.sports,
                            paused: this.series.config.paused,
                            location: this.series.config.location,
                            airByDate: this.series.config.airByDate,
                            subtitlesEnabled: this.series.config.subtitlesEnabled,
                            release: {
                                requiredWords: this.series.config.release.requiredWords,
                                ignoredWords: this.series.config.release.ignoredWords
                            },
                            qualities: {
                                preferred: this.series.config.qualities.preferred,
                                allowed: this.series.config.qualities.allowed
                            }
                        },
                        language: this.series.language
                    };

                    if (data.config.anime) {
                        data.config.release.blacklist = this.series.config.release.blacklist;
                        data.config.release.whitelist = this.series.config.release.whitelist;
                    }

                    try {
                        const response = await api.patch('series/' + this.seriesSlug, data);
                        this.$snotify.success('You may need to "Re-scan files" or "Force Full Update".', 'Saved', { timeout: 5000 });

                    } catch (error) {
                        this.$snotify.error(
                            'Error while trying to save "' + this.series.title + '": ' + error.message || 'Unknown',
                            'Error'
                        );
                    }
                };

                // Re-enable the save button.
                this.saving = false;
            },
            onChangeIgnoredWords(items) {
                this.series.config.release.ignoredWords = items.map(item => item.value);
            },
            onChangeRequiredWords(items) {
                this.series.config.release.requiredWords = items.map(item => item.value);
            },
            onChangeAliases(items) {
                this.series.config.aliases = items.map(item => item.value);
            },
            onChangeReleaseGroupsAnime(items) {
                this.series.config.release.whitelist = items.filter(item => item.memberOf === 'whitelist');
                this.series.config.release.blacklist = items.filter(item => item.memberOf === 'blacklist');
                this.series.config.release.allgroups = items.filter(item => item.memberOf === 'releasegroups');
            },
            updateLanguage(value) {
                this.series.language = value;
            }
        },
        computed: {
            availableLanguages() {
                if (this.config.indexers.config.main.validLanguages) {
                    return this.config.indexers.config.main.validLanguages.join(',');
                }
            },
            combinedQualities() {
                const reducer = (accumulator, currentValue) => accumulator | currentValue;
                const allowed = this.series.config.qualities.allowed.reduce(reducer, 0);
                const preferred = this.series.config.qualities.preferred.reduce(reducer, 0);

                return allowed | preferred << 16
            },
            saveButton() {
                return this.saving === false ? 'Save Changes' : 'Saving...';
            },
            displayShowUrl() {
                // @TODO: Change the URL generation to use `this.series`. Currently not possible because
                // the values are not available at the time of app-link component creation.
                return window.location.pathname.replace('editShow', 'displayShow') + window.location.search;
            }
        }
    });
};
</script>
</%block>
<%block name="content">
<vue-snotify></vue-snotify>
<input type="hidden" id="indexer-name" value="${show.indexer_name}" />
<input type="hidden" id="series-id" value="${show.indexerid}" />
<input type="hidden" id="series-slug" value="${show.slug}" />
<h1 class="header">
    Edit Show
    <span v-show="series.title"> - <app-link :href="displayShowUrl">{{series.title}}</app-link></span>
</h1>
<div id="config-content">
    <div id="config" :class="{ summaryFanArt: config.fanartBackground }">
        <form @submit.prevent="saveSeries('all')" class="form-horizontal">
        <div id="config-components">
            <ul>
                <li><app-link href="#core-component-group1">Main</app-link></li>
                <li><app-link href="#core-component-group2">Format</app-link></li>
                <li><app-link href="#core-component-group3">Advanced</app-link></li>
            </ul>
            <div id="core-component-group1">
                <div class="component-group">
                    <h3>Main Settings</h3>
                    <fieldset class="component-group-list">
                        <div class="form-group">
                            <label for="location" class="col-sm-2 control-label">Show Location</label>
                            <div class="col-sm-10 content">
                                <input type="hidden" name="indexername" id="form-indexername" :value="indexerName"/>
                                <input type="hidden" name="seriesid" id="form-seriesid" :value="seriesId" />
                                <file-browser name="location" ref="locationBrowser" id="location" title="Select Show Location" :initial-dir="series.config.location" @update:location="series.config.location = $event"/>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="qualityPreset" class="col-sm-2 control-label">Preferred Quality</label>
                            <div class="col-sm-10 content">
                                <quality-chooser :overall-quality="combinedQualities" @update:quality:allowed="series.config.qualities.allowed = $event" @update:quality:preferred="series.config.qualities.preferred = $event"></quality-chooser>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="defaultEpStatusSelect" class="col-sm-2 control-label">Default Episode Status</label>
                            <div class="col-sm-10 content">
                                <select name="defaultEpStatus" id="defaultEpStatusSelect" class="form-control form-control-inline input-sm"
                                    v-model="series.config.defaultEpisodeStatus"/>
                                    <option v-for="option in defaultEpisodeStatusOptions" :value="option.value">{{ option.text }}</option>
                                </select>
                                <div class="clear-left"><p>This will set the status for future episodes.</p></div>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="indexerLangSelect" class="col-sm-2 control-label">Info Language</label>
                            <div class="col-sm-10 content">
                                <language-select id="indexerLangSelect" @update-language="updateLanguage" :language="series.language" :available="availableLanguages" name="indexer_lang" id="indexerLangSelect" class="form-control form-control-inline input-sm"></language-select>
                                <div class="clear-left"><p>This only applies to episode filenames and the contents of metadata files.</p></div>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="subtitles" class="col-sm-2 control-label">Subtitles</label>
                            <div class="col-sm-10 content">
                                <input type="checkbox" id="subtitles" name="subtitles" v-model="series.config.subtitlesEnabled"/> search for subtitles
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="paused" class="col-sm-2 control-label">Paused</label>
                            <div class="col-sm-10 content">
                                <input type="checkbox" id="paused" name="paused" v-model="series.config.paused"/> pause this show (Medusa will not download episodes)
                            </div>
                        </div>
                    </fieldset>
                </div>
            </div>
            <div id="core-component-group2">
                <div class="component-group">
                    <h3>Format Settings</h3>
                    <fieldset class="component-group-list">

                        <div class="form-group">
                            <label for="airbydate" class="col-sm-2 control-label">Air by date</label>
                            <div class="col-sm-10 content">
                                <input type="checkbox" id="airbydate" name="air_by_date" v-model="series.config.airByDate" /> check if the show is released as Show.03.02.2010 rather than Show.S02E03.<br>
                                <span style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</span>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="anime" class="col-sm-2 control-label">Anime</label>
                            <div class="col-sm-10 content">
                                <input type="checkbox" id="anime" name="anime" v-model="series.config.anime"> check if the show is Anime and episodes are released as Show.265 rather than Show.S02E03<br>
                            </div>
                        </div>

                        <div v-if="series.config.anime" class="form-group">
                            <label for="anidbReleaseGroup" class="col-sm-2 control-label">Release Groups</label>
                            <div class="col-sm-10 content">
                                <anidb-release-group-ui class="max-width" :blacklist="series.config.release.blacklist" :whitelist="series.config.release.whitelist" :all-groups="series.config.release.allgroups" @change="onChangeReleaseGroupsAnime"></anidb-release-group-ui>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="sports" class="col-sm-2 control-label">Sports</label>
                            <div class="col-sm-10 content">
                                <input type="checkbox" id="sports" name="sports" v-model="series.config.sports"/> check if the show is a sporting or MMA event released as Show.03.02.2010 rather than Show.S02E03<br>
                                <span style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</span>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="season_folders" class="col-sm-2 control-label">Season folders</label>
                            <div class="col-sm-10 content">
                                <input type="checkbox" id="season_folders" name="season_folders" v-model="series.config.seasonFolders"/> group episodes by season folder (uncheck to store in a single folder)
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="scene" class="col-sm-2 control-label">Scene Numbering</label>
                            <div class="col-sm-10 content">
                                <input type="checkbox" id="scene" name="scene" v-model="series.config.scene"/> search by scene numbering (uncheck to search by indexer numbering)
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="dvdorder" class="col-sm-2 control-label">DVD Order</label>
                            <div class="col-sm-10 content">
                                <input type="checkbox" id="dvdorder" name="dvd_order" v-model="series.config.dvdOrder"/> use the DVD order instead of the air order<br>
                                <div class="clear-left"><p>A "Force Full Update" is necessary, and if you have existing episodes you need to sort them manually.</p></div>
                            </div>
                        </div>
                    </fieldset>
                </div>
            </div>
            <div id="core-component-group3">
                <div class="component-group">
                    <h3>Advanced Settings</h3>
                    <fieldset class="component-group-list">

                        <div class="form-group">
                            <label for="rls_ignore_words" class="col-sm-2 control-label">Ignored words</label>
                            <div class="col-sm-10 content">
                                <select-list :list-items="series.config.release.ignoredWords" @change="onChangeIgnoredWords"></select-list>
                                <div class="clear-left">
                                    <p>Search results with one or more words from this list will be ignored.</p>
                                </div>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="rls_require_words" class="col-sm-2 control-label">Required words</label>
                            <div class="col-sm-10 content">
                                <select-list :list-items="series.config.release.requiredWords" @change="onChangeRequiredWords"></select-list>
                                <div class="clear-left">
                                    <p>Search results with no words from this list will be ignored.</p>
                                </div>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="SceneName" class="col-sm-2 control-label">Scene Exception</label>
                            <div class="col-sm-10 content">
                                <select-list :list-items="series.config.aliases" @change="onChangeAliases"></select-list>
                                <div class="clear-left">
                                    <p>This will affect episode search on NZB and torrent providers. This list appends to the original show name.</p>
                                </div>
                            </div>
                        </div>

                    </fieldset>
                </div>
            </div>
        </div>
        <br>
        <input id="submit" type="submit" :value="saveButton" class="btn-medusa pull-left button" :disabled="saving || !seriesLoaded">
        </form>
    </div>
</div>
</%block>
