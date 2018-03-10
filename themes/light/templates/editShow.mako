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
<%block name="content">
<input type="hidden" id="indexer-name" value="${show.indexer_name}" />
<input type="hidden" id="series-id" value="${show.indexerid}" />
<input type="hidden" id="series-slug" value="${show.slug}" />
% if not header is UNDEFINED:
    <h1 class="header">${header}</h1>
% else:
    <h1 class="title">${title}</h1>
% endif
<div id="config-content">
    <div id="config" :class="{ summaryFanArt: config.fanartBackground }">
        <form @submit.prevent="saveSeries('all')">
        <div id="config-components">
            <ul>
                <li><a href="${full_url}#core-component-group1">Main</a></li>
                <li><a href="${full_url}#core-component-group2">Format</a></li>
                <li><a href="${full_url}#core-component-group3">Advanced</a></li>
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
                                    <input type="hidden" name="seriesid" id="form-seriesid" :value="seriesId"/>
                                    <input type="text" name="location" id="location" :value="seriesObj.config.location" class="form-control form-control-inline input-sm input350" @change="saveSeries()"/>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="qualityPreset">
                                <span class="component-title">Preferred Quality</span>
                                <!-- TODO: replace these with a vue component -->
                                <span class="component-desc">
                                    <% allowed_qualities, preferred_qualities = common.Quality.split_quality(int(show.quality)) %>
                                    <%include file="/inc_qualityChooser.mako"/>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="defaultEpStatusSelect">
                                <span class="component-title">Default Episode Status</span>
                                <span class="component-desc">
                                    <select name="defaultEpStatus" id="defaultEpStatusSelect" class="form-control form-control-inline input-sm" 
                                        v-model="seriesObj.config.defaultEpisodeStatus"  @change="saveSeries('seriesObj')"/>
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
                                    <select name="indexer_lang" id="indexerLangSelect" class="form-control form-control-inline input-sm bfh-languages" 
                                        data-blank="false" :data-language="seriesObj.language" :data-available="availableLanguages" @change="saveSeries('seriesObj')">
                                    </select>
                                    <div class="clear-left"><p>This only applies to episode filenames and the contents of metadata files.</p></div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="subtitles">
                                <span class="component-title">Subtitles</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="subtitles" name="subtitles" v-model="seriesObj.config.subtitlesEnabled" @change="saveSeries('seriesObj')"/> search for subtitles
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="paused">
                                <span class="component-title">Paused</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="paused" name="paused" v-model="seriesObj.config.paused" @change="saveSeries('seriesObj')"/> pause this show (Medusa will not download episodes)
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
                                    <input type="checkbox" id="airbydate" name="air_by_date" v-model="seriesObj.config.paused" @change="saveSeries('seriesObj')" /> check if the show is released as Show.03.02.2010 rather than Show.S02E03.<br>
                                    <span style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</span>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="anime">
                                <span class="component-title">Anime</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="anime" name="anime" v-model="seriesObj.config.anime" @change="saveSeries('seriesObj')"> check if the show is Anime and episodes are released as Show.265 rather than Show.S02E03<br>
                                </span>
                            </label>
                        </div>
                        
                        <div v-if="seriesObj.config.anime" class="field-pair">
                            <span class="component-title">Release Groups</span>
                            <span class="component-desc">
                                <anidb-release-group-ui :series="seriesSlug" :blacklist="seriesObj.config.release.blacklist" :whitelist="seriesObj.config.release.whitelist" :all-groups="['group1', 'group2']"></anidb-release-group-ui>
                            </span>
                        </div>

                        <div class="field-pair">
                            <label for="sports">
                                <span class="component-title">Sports</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="sports" name="sports" v-model="seriesObj.config.sports" @change="saveSeries('seriesObj')"/> check if the show is a sporting or MMA event released as Show.03.02.2010 rather than Show.S02E03<br>
                                    <span style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</span>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="season_folders">
                                <span class="component-title">Season folders</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="season_folders" name="flatten_folders" v-model="seriesObj.config.flattenFolders" @change="saveSeries('seriesObj')"/> group episodes by season folder (uncheck to store in a single folder)
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="scene">
                                <span class="component-title">Scene Numbering</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="scene" name="scene" v-model="seriesObj.config.scene" @change="saveSeries('seriesObj')"/> search by scene numbering (uncheck to search by indexer numbering)
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="dvdorder">
                                <span class="component-title">DVD Order</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="dvdorder" name="dvd_order" v-model="seriesObj.config.dvdOrder" @change="saveSeries('seriesObj')"/> use the DVD order instead of the air order<br>
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
                                    <select-list v-if="seriesObj.config.release.ignoredWords !== null" :list-items="seriesObj.config.release.ignoredWords" @change="onChangeIgnoredWords"></select-list>
                                    <div class="clear-left">
                                        <p>comma-separated <i>e.g. "word1,word2,word3"</i></p>
                                        <p>Search results with one or more words from this list will be ignored.</p>
                                    </div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="rls_require_words">
                                <span class="component-title">Required Words</span>
                                <span class="component-desc">
                                    <select-list v-if="seriesObj.config.release.requiredWords !== null" :list-items="seriesObj.config.release.requiredWords" @change="onChangeRequiredWords"></select-list>
                                    <div class="clear-left">
                                        <p>comma-separated <i>e.g. "word1,word2,word3"</i></p>
                                        <p>Search results with no words from this list will be ignored.</p>
                                    </div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="SceneName">
                                <span class="component-title">Scene Exception</span>
                                <span class="component-desc">
                                    <select-list v-if="seriesObj.config.aliases" :list-items="seriesObj.config.aliases" @change="onChangeAliases"></select-list>
                                    
                                    <!-- <input type="text" id="SceneName" class="form-control form-control-inline input-sm input200"/><input class="btn btn-inline" type="button" value="Add" id="addSceneName" /><br><br>
                                    <div class="pull-left">
                                        <select id="exceptions_list" name="exceptions_list" multiple="multiple" style="min-width:200px;height:99px;">
                                            <option v-for="exception in exceptions" :value="exception.series_name">
                                                {{exception.series_name}} ({{exception.episode_search_template}})
                                            </option>
                                        </select>
                                        <div><input id="removeSceneName" value="Remove" class="btn float-left" type="button" style="margin-top: 10px;"/></div>
                                    </div> -->
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
<%block name="scripts">
    <script type="text/javascript" src="js/quality-chooser.js?${sbPID}"></script>
    <script type="text/javascript" src="js/edit-show.js"></script>
<script src="js/lib/vue.js"></script>
<%include file="/vue-components/selectListUi.mako"/>
<%include file="/vue-components/anidbReleaseGroupUi.mako"/>
<script>
var startVue = function() {
    const app = new Vue({
        el: '#config-content',
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
                seriesObj: {
                    config: {
                        dvdOrder: false,
                        flattenFolders: false,
                        anime: false,
                        scene: false,
                        sports: false,
                        paused: false,
                        location: "",
                        airByDate: false,
                        subtitlesEnabled: false,
                        release: {
                            requiredWords: null,
                            ignoredWords: null,
                            blacklist: [],
                            whitelist: []
                        }
                    },
                    language: ''
                },
                defaultEpisodeStatusOptions: [
                    {text: 'Wanted', value: 'Wanted'},
                    {text: 'Skipped', value: 'Skipped'},
                    {text: 'Ignored', value: 'Ignored'}
                ],
                saveStatus: '',
                seriesLoaded: false
            }
        },
        async mounted() {
            const seriesSlug = $('#series-slug').attr('value');
            const url = 'series/' + seriesSlug;
            try {
                const response = await api.get('series/' + this.seriesSlug);
                this.seriesObj.config = response.data.config;
            } catch (error) {
                console.log('Could not get series info for: '+ seriesSlug);
            }
        },
        methods: {
            anonRedirect: function(e) {
                e.preventDefault();
                window.open(MEDUSA.info.anonRedirect + e.target.href, '_blank');
            },
            prettyPrintJSON: function(x) {
                return JSON.stringify(x, undefined, 4)
            },
            loadSeries: async function() {

            },
            saveSeries: async function(subject) {
                if (['seriesObj', 'all'].includes(subject)) {
                    const data = {
                        config: {
                            aliases: this.seriesObj.config.aliases,
                            dvdOrder: this.seriesObj.config.dvdOrder,
                            flattenFolders: this.seriesObj.config.flattenFolders,
                            anime: this.seriesObj.config.anime,
                            scene: this.seriesObj.config.scene,
                            sports: this.seriesObj.config.sports,
                            paused: this.seriesObj.config.paused,
                            location: this.seriesObj.config.location,
                            airByDate: this.seriesObj.config.airByDate,
                            subtitlesEnabled: this.seriesObj.config.subtitlesEnabled,
                            release: {
                                requiredWords: this.seriesObj.config.release.requiredWords,
                                ignoredWords: this.seriesObj.config.release.ignoredWords
                                // blacklist: this.seriesObj.config.release.blacklist,
                                // whitelist: this.seriesObj.config.release.whitelist
                            }
                        }
                    };
                    try {
                        const response = await api.patch('series/' + this.seriesSlug, data);
                        this.saveStatus = 'Successfully patched series';
                    } catch (error) {
                        this.saveStatus = 'Problem trying to save series with error' + error + ', sending data: ' + data;
                    }
                };
            },
            onChangeIgnoredWords: function(items) {
		        console.log('Event from child component emitted', items);
                this.seriesObj.config.release.ignoredWords = items.map(item => item.value);
            },
            onChangeRequiredWords: function(items) {
		        console.log('Event from child component emitted', items);
                this.seriesObj.config.release.requiredWords = items.map(item => item.value);
            },
            onChangeAliases: function(items) {
		        console.log('Event from child component emitted', items);
                this.seriesObj.config.aliases = items.map(item => item.value);
            }
        },
        computed: {
            availableLanguages: function() {
                if (this.config.indexers.config.main.validLanguages){
                    return this.config.indexers.config.main.validLanguages.join(',');
                }
            }
        }
    });
    $('[v-cloak]').removeAttr('v-cloak');
};
</script>
</%block>
