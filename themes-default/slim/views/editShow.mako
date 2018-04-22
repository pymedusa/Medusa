<%inherit file="/layouts/main.mako"/>
<%!
    import adba
    import json
    from medusa import app, common
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from medusa.common import statusStrings
    from medusa.helper import exceptions
    from medusa.indexers.indexer_api import indexerApi
    from medusa.indexers.utils import mappings
    from medusa import scene_exceptions
%>
<%block name="metas">
<meta data-var="show.is_anime" data-content="${show.is_anime}">
</%block>
<link rel="stylesheet" type="text/css" href="css/vue/editshow.css?${sbPID}" />
<%block name="scripts">
<%include file="/vue-components/quality-chooser.mako"/>
<%include file="/vue-components/select-list-ui.mako"/>
<%include file="/vue-components/anidb-release-group-ui.mako"/>

<script>
const startVue = () => {
    const app = new Vue({
        el: '#vue-wrap',
        data() {
            // Python conversions
            // JS only
            const exceptions = [];
            return {
                seriesSlug: $('#series-slug').attr('value'),
                seriesId: $('#series-id').attr('value'),
                indexerName: $('#indexer-name').attr('value'),
                config: MEDUSA.config,
                exceptions: exceptions,
                series: {
                    config: {
                        dvdOrder: false,
                        flattenFolders: false,
                        anime: false,
                        scene: false,
                        sports: false,
                        paused: false,
                        location: '',
                        airByDate: false,
                        subtitlesEnabled: false,
                        release: {
                            requiredWords: null,
                            ignoredWords: null,
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
                location: '',
                saveMessage: '',
                saveError: '',
                mounted: false
            }
        },
        async mounted() {
            const seriesSlug = $('#series-slug').attr('value');
            const url = 'series/' + seriesSlug;
            try {
                const response = await api.get('series/' + this.seriesSlug);
                this.series = Object.assign({}, this.series, response.data);
                this.series.language = response.data.language;
                this.location = this.series.config.location;
            } catch (error) {
                console.debug('Could not get series info for: '+ seriesSlug);
            }

            // Add the Browse.. button after the show location input.
            $('#location').fileBrowser({
	            title: 'Select Show Location'
            });
            this.mounted = true;
        },
        methods: {
            anonRedirect: function(e) {
                e.preventDefault();
                window.open(MEDUSA.info.anonRedirect + e.target.href, '_blank');
            },
            prettyPrintJSON: function(x) {
                return JSON.stringify(x, undefined, 4)
            },
            saveSeries: async function(subject) {
                // We want to wait until the page has been fully loaded, before starting to save stuff.
                if (!this.mounted) {
                    return;
                }

                if (['series', 'all'].includes(subject)) {
                    const data = {
                        config: {
                            aliases: this.series.config.aliases,
                            dvdOrder: this.series.config.dvdOrder,
                            flattenFolders: this.series.config.flattenFolders,
                            anime: this.series.config.anime,
                            scene: this.series.config.scene,
                            sports: this.series.config.sports,
                            paused: this.series.config.paused,
                            location: this.series.config.location,
                            airByDate: this.series.config.airByDate,
                            subtitlesEnabled: this.series.config.subtitlesEnabled,
                            release: {
                                requiredWords: this.series.config.release.requiredWords,
                                ignoredWords: this.series.config.release.ignoredWords,
                                blacklist: this.series.config.release.blacklist,
                                whitelist: this.series.config.release.whitelist
                            },
                            qualities: {
                                preferred: this.series.config.qualities.preferred,
                                allowed: this.series.config.qualities.allowed,
                                combined: this.combineQualities()
                            }
                        },
                        language: this.series.language
                    };
                    try {
                        this.saveMessage = 'saving';
                        const response = await api.patch('series/' + this.seriesSlug, data);
                        this.saveMessage = 'saved';

                    } catch (error) {
                        this.saveError = 'Problem trying to save the config: ' + error.message || '';
                    }
                };
            },
            onChangeIgnoredWords: function(items) {
		        console.debug('Event from child component emitted', items);
                this.series.config.release.ignoredWords = items.map(item => item.value);
            },
            onChangeRequiredWords: function(items) {
		        console.debug('Event from child component emitted', items);
                this.series.config.release.requiredWords = items.map(item => item.value);
            },
            onChangeAliases: function(items) {
		        console.debug('Event from child component emitted', items);
                this.series.config.aliases = items.map(item => item.value);
            },
            onChangeReleaseGroupsAnime: function(items) {
                this.series.config.release.whitelist = items.filter(item => item.memberOf === 'whitelist');
                this.series.config.release.blacklist = items.filter(item => item.memberOf === 'blacklist');
                this.series.config.release.allgroups = items.filter(item => item.memberOf === 'releasegroups');

            },
            saveLocation: function(value) {
                this.series.config.location = value;
            },
            updateLanguage: function(value) {
                this.series.language = value;
            },
            combineQualities() {
                const reducer = (accumulator, currentValue) => accumulator + currentValue;
                
                const allowed = this.series.config.qualities.allowed.reduce(reducer, 0);
                const preferred = this.series.config.qualities.preferred.reduce(reducer, 0);

                return  allowed | preferred << 16
            }
        },
        computed: {
            availableLanguages: function() {
                if (this.config.indexers.config.main.validLanguages) {
                    return this.config.indexers.config.main.validLanguages.join(',');
                }
            }
        }
    });
};
</script>
</%block>
<%block name="content">
<input type="hidden" id="indexer-name" value="${show.indexer_name}" />
<input type="hidden" id="series-id" value="${show.indexerid}" />
<input type="hidden" id="series-slug" value="${show.slug}" />
% if not header is UNDEFINED:
    <h1 class="header">${header}</h1>
% else:
    <h1 class="title">${title}</h1>
% endif
<saved-message :state="saveMessage" :error="saveError"></saved-message>
<div id="config-content">
    <div id="config" :class="{ summaryFanArt: config.fanartBackground }">
        <form @submit.prevent="saveSeries('all')">
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
                        <div class="field-pair">
                            <label for="location">
                                <span class="component-title">Show Location</span>
                                <span class="component-desc">
                                    <input type="hidden" name="indexername" id="form-indexername" :value="indexerName" />
                                    <input type="hidden" name="seriesid" id="form-seriesid" :value="seriesId" />
                                    <file-browser name="location" ref="locationBtn" id="location" v-model="location"></file-browser>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="qualityPreset">
                                <span class="component-title">Preferred Quality</span>
                                <!-- TODO: replace these with a vue component -->
                                <span class="component-desc">
                                    <quality-chooser @update:quality:allowed="series.config.qualities.allowed = $event" @update:quality:preferred="series.config.qualities.preferred = $event"></quality-chooser>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="defaultEpStatusSelect">
                                <span class="component-title">Default Episode Status</span>
                                <span class="component-desc">
                                    <select name="defaultEpStatus" id="defaultEpStatusSelect" class="form-control form-control-inline input-sm"
                                        v-model="series.config.defaultEpisodeStatus"  @change="saveSeries('series')"/>
                                        <option v-for="option in defaultEpisodeStatusOptions" :value="option.value">{{ option.text }}</option>
                                    </select>
                                    <div class="clear-left"><p>This will set the status for future episodes.</p></div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="indexerLangSelect">
                                <span class="component-title">Info Language</span>
                                <span class="component-desc">
                                    <language-select @update-language="updateLanguage" v-if="series.language" :language="series.language" :available="availableLanguages" name="indexer_lang" id="indexerLangSelect" class="form-control form-control-inline input-sm">
                                    </language-select>
                                    <div class="clear-left"><p>This only applies to episode filenames and the contents of metadata files.</p></div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="subtitles">
                                <span class="component-title">Subtitles</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="subtitles" name="subtitles" v-model="series.config.subtitlesEnabled" @change="saveSeries('series')"/> search for subtitles
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="paused">
                                <span class="component-title">Paused</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="paused" name="paused" v-model="series.config.paused" @change="saveSeries('series')"/> pause this show (Medusa will not download episodes)
                                </span>
                            </label>
                        </div>
                    </fieldset>
                </div>
            </div>
            <div id="core-component-group2">
                <div class="component-group">
                    <h3>Format Settings</h3>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="airbydate">
                                <span class="component-title">Air by date</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="airbydate" name="air_by_date" v-model="series.config.paused" @change="saveSeries('series')" /> check if the show is released as Show.03.02.2010 rather than Show.S02E03.<br>
                                    <span style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</span>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="anime">
                                <span class="component-title">Anime</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="anime" name="anime" v-model="series.config.anime" @change="saveSeries('series')"> check if the show is Anime and episodes are released as Show.265 rather than Show.S02E03<br>
                                </span>
                            </label>
                        </div>

                        <div v-if="series.config.anime" class="field-pair">
                            <span class="component-title">Release Groups</span>
                            <span class="component-desc">
                                <anidb-release-group-ui :blacklist="series.config.release.blacklist" :whitelist="series.config.release.whitelist" :all-groups="series.config.release.allgroups" @change="onChangeReleaseGroupsAnime"></anidb-release-group-ui>
                            </span>
                        </div>

                        <div class="field-pair">
                            <label for="sports">
                                <span class="component-title">Sports</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="sports" name="sports" v-model="series.config.sports" @change="saveSeries('series')"/> check if the show is a sporting or MMA event released as Show.03.02.2010 rather than Show.S02E03<br>
                                    <span style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</span>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="season_folders">
                                <span class="component-title">Season folders</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="season_folders" name="flatten_folders" v-model="series.config.flattenFolders" @change="saveSeries('series')"/> group episodes by season folder (uncheck to store in a single folder)
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="scene">
                                <span class="component-title">Scene Numbering</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="scene" name="scene" v-model="series.config.scene" @change="saveSeries('series')"/> search by scene numbering (uncheck to search by indexer numbering)
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="dvdorder">
                                <span class="component-title">DVD Order</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="dvdorder" name="dvd_order" v-model="series.config.dvdOrder" @change="saveSeries('series')"/> use the DVD order instead of the air order<br>
                                    <div class="clear-left"><p>A "Force Full Update" is necessary, and if you have existing episodes you need to sort them manually.</p></div>
                                </span>
                            </label>
                        </div>
                    </fieldset>
                </div>
            </div>
            <div id="core-component-group3">
                <div class="component-group">
                    <h3>Advanced Settings</h3>
                    <fieldset class="component-group-list">
                        <div class="field-pair">
                            <label for="rls_ignore_words">
                                <span class="component-title">Ignored Words</span>
                                <span class="component-desc">
                                    <select-list v-if="series.config.release.ignoredWords !== null" :list-items="series.config.release.ignoredWords" @change="onChangeIgnoredWords"></select-list>
                                    <div class="clear-left">
                                        <p>Search results with one or more words from this list will be ignored.</p>
                                    </div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="rls_require_words">
                                <span class="component-title">Required Words</span>
                                <span class="component-desc">
                                    <select-list v-if="series.config.release.requiredWords !== null" :list-items="series.config.release.requiredWords" @change="onChangeRequiredWords"></select-list>
                                    <div class="clear-left">
                                        <p>Search results with no words from this list will be ignored.</p>
                                    </div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="SceneName">
                                <span class="component-title">Scene Exception</span>
                                <span class="component-desc">
                                    <select-list v-if="series.config.aliases" :list-items="series.config.aliases" @change="onChangeAliases"></select-list>
                                    <div class="clear-left"><p>This will affect episode search on NZB and torrent providers. This list appends to the original show name.</p></div>
                                </span>
                            </label>
                        </div>
                    </fieldset>
                </div>
            </div>
        </div>
        <br>
        <input id="submit" type="submit" value="Save Changes" class="btn pull-left config_submitter button">
        </form>
    </div>
</div>
</%block>
