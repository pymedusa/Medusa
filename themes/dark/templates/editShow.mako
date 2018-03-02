<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import common
%>
<%block name="metas">
<meta data-var="show.is_anime" data-content="${show.is_anime}">
</%block>
<%block name="content">
<input type="hidden" id="indexer-name" value="${show.indexer_name}" />
<input type="hidden" id="series-id" value="${show.indexerid}" />
<input type="hidden" id="series-slug" value="${show.slug}" />
<h1 v-if="header" class="header">{{header}}</h1>
<h1 v-else class="title">{{title}}</h1>
<div id="config-content">
    <div id="config" v-bind:class="{ summaryFanArt: config.fanartBackground }">
        <form @submit.prevent="storeConfig('all')">
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
                                    <input type="text" name="location" id="location" :value="series.config.location" class="form-control form-control-inline input-sm input350" @change="storeConfig()"/>
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
                                    <select name="defaultEpStatus" id="defaultEpStatusSelect" class="form-control form-control-inline input-sm" v-model="series.config.defaultEpisodeStatus"  @change="storeConfig('series')">
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
                                    <select name="indexer_lang" id="indexerLangSelect" class="form-control form-control-inline input-sm bfh-languages" data-blank="false" :data-language="series.language" :data-available="availableLanguages" @change="storeConfig('series')">
                                    </select>
                                    <div class="clear-left"><p>This only applies to episode filenames and the contents of metadata files.</p></div>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="subtitles">
                                <span class="component-title">Subtitles</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="subtitles" name="subtitles" v-model="series.config.subtitlesEnabled" @change="storeConfig('series')"/> search for subtitles
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="paused">
                                <span class="component-title">Paused</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="paused" name="paused" v-model="series.config.paused" @change="storeConfig('series')"/> pause this show (Medusa will not download episodes)
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
                                    <input type="checkbox" id="airbydate" name="air_by_date" v-model="series.config.paused" @change="storeConfig('series')" /> check if the show is released as Show.03.02.2010 rather than Show.S02E03.<br>
                                    <span style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</span>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="anime">
                                <span class="component-title">Anime</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="anime" name="anime" v-model="series.config.anime" @change="storeConfig('series')"> check if the show is Anime and episodes are released as Show.265 rather than Show.S02E03<br>
                                </span>
                            </label>
                        </div>

                        <div v-if="series.config.anime" class="field-pair">
                            <span class="component-title">Release Groups</span>
                            <span class="component-desc">
                                <anidb-release-group-ui :series="seriesSlug" :blacklist="series.config.release.blacklist" :whitelist="series.config.release.whitelist" :all-groups="['group1', 'group2']"></anidb-release-group-ui>
                            </span>
                        </div>

                        <div class="field-pair">
                            <label for="sports">
                                <span class="component-title">Sports</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="sports" name="sports" v-model="series.config.sports" @change="storeConfig('series')"/> check if the show is a sporting or MMA event released as Show.03.02.2010 rather than Show.S02E03<br>
                                    <span style="color:rgb(255, 0, 0);">In case of an air date conflict between regular and special episodes, the later will be ignored.</span>
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="season_folders">
                                <span class="component-title">Season folders</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="season_folders" name="flatten_folders" v-model="series.config.flattenFolders" @change="storeConfig('series')"/> group episodes by season folder (uncheck to store in a single folder)
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="scene">
                                <span class="component-title">Scene Numbering</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="scene" name="scene" v-model="series.config.scene" @change="storeConfig('series')"/> search by scene numbering (uncheck to search by indexer numbering)
                                </span>
                            </label>
                        </div>
                        <div class="field-pair">
                            <label for="dvdorder">
                                <span class="component-title">DVD Order</span>
                                <span class="component-desc">
                                    <input type="checkbox" id="dvdorder" name="dvd_order" v-model="series.config.dvdOrder" @change="storeConfig('series')"/> use the DVD order instead of the air order<br>
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
                                    <select-list v-if="ignoredWords" :list-items="ignoredWords" @change="onChangeIgnoredWords"></select-list>
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
                                    <select-list v-if="requiredWords" :list-items="requiredWords" @change="onChangeRequiredWords"></select-list>
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
                                    <input type="text" id="SceneName" class="form-control form-control-inline input-sm input200"/><input class="btn btn-inline" type="button" value="Add" id="addSceneName" /><br><br>
                                    <div class="pull-left">
                                        <select id="exceptions_list" name="exceptions_list" multiple="multiple" style="min-width:200px;height:99px;">
                                            <option v-for="exception in exceptions" :value="exception.series_name">
                                                {{exception.series_name}} ({{exception.episode_search_template}})
                                            </option>
                                        </select>
                                        <div><input id="removeSceneName" value="Remove" class="btn float-left" type="button" style="margin-top: 10px;"/></div>
                                    </div>
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
        el: '#vue-wrap',
        data() {
            return {
                // Python
                header: '${header}',
                title: '${title}',
                // JS
                seriesSlug: $('#series-slug').attr('value'),
                seriesId: $('#series-id').attr('value'),
                indexerName: $('#indexer-name').attr('value'),
                config: MEDUSA.config,
                exceptions: [],
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
                saveStatus: ''
            }
        },
        async mounted() {
            const url = 'series/' + $('#series-slug').attr('value');
            const {data} = await api.get('series/' + this.seriesSlug);
            this.series.config = data.config;
        },
        methods: {
            anonRedirect(e) {
                e.preventDefault();
                window.open(MEDUSA.info.anonRedirect + e.target.href, '_blank');
            },
            prettyPrintJSON(x) {
                return JSON.stringify(x, undefined, 4)
            },
            storeConfig: async function(subject) {
                if (['series', 'all'].includes(subject)) {
                    const {
                        dvdOrder,
                        flattenFolders,
                        anime,
                        scene,
                        sports,
                        paused,
                        location,
                        airByDate,
                        subtitlesEnabled
                    } = this.series.config;
                    const {requiredWords, ignoredWords} = series.config.release;
                    const data = {
                        config: {
                            dvdOrder,
                            flattenFolders,
                            anime,
                            scene,
                            sports,
                            paused,
                            location,
                            airByDate,
                            subtitlesEnabled,
                            release: {
                                requiredWords,
                                ignoredWords,
                                // blacklist: this.series.config.release.blacklist,
                                // whitelist: this.series.config.release.whitelist
                            }
                        }
                    };
                    const response = await api.patch('series/' + this.seriesSlug, data);
                    if (response.status === 200) {
                        this.saveStatus = 'Successfully patched series';
                    } else {
                        this.saveStatus = 'Problem trying to archive using payload: ' + data;
                    }
                };
            },
            onChangeIgnoredWords(items) {
                this.series.config.release.ignoredWords = items.map(item => item.value);
            },
            onChangeRequiredWords(items) {
                this.series.config.release.requiredWords = items.map(item => item.value);
            },
            transformToIndexedObject: (arrayOfStrings) => (arrayOfStrings || []).map((string, index) => ({id: index, value: string}))
        },
        computed: {
            availableLanguages() {
                const {validLanguages} = this.config.indexers.config.main;
                if (validLanguages){
                    return validLanguages.join(',');
                }
            },
            ignoredWords() {
                return this.transformToIndexedObject(this.series.config.release.ignoredWords);
            },
            requiredWords() {
                return this.transformToIndexedObject(this.series.config.release.requiredWords);
            }
        }
    });
};
</script>
</%block>
