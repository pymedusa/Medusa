<template>
    <div class="display-show-template">
        <backstretch v-bind="{indexer, id}"></backstretch>
        <input type="hidden" id="series-id" value="" />
        <input type="hidden" id="indexer-name" value="" />
        <input type="hidden" id="series-slug" value="" />

        <show-header @reflow="reflowLayout" type="show"
            :show-id="id" :show-indexer="indexer" @update="statusQualityUpdate"
        ></show-header>

        <!-- <subtitle-search v-if="Boolean(show)" :show="show" :season="4" :episode="8"></subtitle-search> -->

        <div class="row">
            <div class="col-md-12 top-15 displayShow" :class="{ fanartBackground: config.fanartBackground }">
                <vue-good-table v-if="show.seasons"
                :columns="columns"
                :rows="show.seasons.slice().reverse()"
                :groupOptions="{
                    enabled: true,
                    mode: 'span',
                    customChildObject: 'episodes'
                }"
                :search-options="{
                    enabled: true,
                    trigger: 'enter',
                    skipDiacritics: false,
                    placeholder: 'Search episodes',
                }"
                :sort-options="{
                    enabled: true,
                    initialSortBy: { field: 'episode', type: 'desc' }
                }"
                :selectOptions="{
                    enabled: true,
                    selectOnCheckboxOnly: true, // only select when checkbox is clicked instead of the row
                    selectionInfoClass: 'select-info',
                    selectionText: 'rows selected',
                    clearSelectionText: 'clear',
                    selectAllByGroup: true
                }"
                :row-style-class="rowStyleClassFn"
                ref='table-seasons'
                @on-selected-rows-change="selectedEpisodes=$event.selectedRows">
                <div slot="table-actions">
                    <!-- Drowdown with checkboxes for showing / hiding table headers -->
                    <div class="button-group pull-right">
                        <button type="button" class="btn btn-default btn-sm dropdown-toggle" data-toggle="dropdown"><span class="fa fa-cog" aria-hidden="false">Select Columns</span> <span class="caret"></span></button>
                        <ul class="dropdown-menu" style="top: auto; left: auto;">
                            <li v-for="(column, index) in columns" :key="index">
                                <a href="#" class="small" tabIndex="-1" @click="toggleColumn( index, $event )"><input :checked="!column.hidden" type="checkbox"/>{{column.label}}</a>
                            </li>
                        </ul>
                    </div>
                </div>

                <template slot="table-header-row" slot-scope="props" :class="'my-class'">
                    <h3 class="season-header"><app-link :name="'season-'+ props.row.season"></app-link>
                        <!-- {'Season ' + str(epResult['season']) if int(epResult['season']) > 0 else 'Specials'} -->
                        {{ props.row.label > 0 ? 'Season ' + props.row.label : 'Specials' }}
                        <!-- Only show the search manual season search, when any of the episodes in it is not unaired -->
                        <app-link v-if="anyEpisodeNotUnaired(props.row)" class="epManualSearch" :href="'home/snatchSelection?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&amp;season=' + props.row.season + '&amp;episode=1&amp;manual_search_type=season'">
                            <img v-if="config" data-ep-manual-search :src="'images/manualsearch' + (config.themeName === 'dark' ? '-white' : '') + '.png'" width="16" height="16" alt="search" title="Manual Search" />
                        </app-link>
                    </h3>
                </template>
                                
                <template slot="table-row" slot-scope="props">
                    <span v-if="props.column.field == 'content.hasNfo'">
                        <img :src="'images/' + (props.row.content.hasNfo ? 'nfo.gif' : 'nfo-no.gif')" :alt="(props.row.content.hasNfo ? 'Y' : 'N')" width="23" height="11" />
                    </span>
                    <span v-else-if="props.column.field == 'content.hasTbn'">
                        <img :src="'images/' + (props.row.content.hasTbn ? 'tbn.gif' : 'tbn-no.gif')" :alt="(props.row.content.hasTbn ? 'Y' : 'N')" width="23" height="11" />
                    </span>
                    <span v-else-if="props.column.field == 'download'">
                        <app-link v-if="config.downloadUrl && props.row.file.location && ['Downloaded', 'Archived'].includes(props.row.status)" :href="config.downloadUrl + props.row.file.location">Download</app-link>
                    </span>

                    <span v-else-if="props.column.field == 'episode'">
                        <span :title="props.row.location !== '' ? props.row.location : ''" :class="{addQTip: props.row.location !== ''}">{{props.row.episode}}</span>
                    </span>

                    <span v-else-if="props.column.field == 'scene'">
                        <input type="text" :placeholder="getSceneNumbering(props.row).season + 'x' + getSceneNumbering(props.row).episode" size="6" maxlength="8"
                            class="sceneSeasonXEpisode form-control input-scene" :data-for-season="props.row.season" :data-for-episode="props.row.episode"
                            :id="'sceneSeasonXEpisode_' + show.id[show.indexer] + '_' + props.row.season + '_' + props.row.episode"
                            title="Change this value if scene numbering differs from the indexer episode numbering. Generally used for non-anime shows."
                            :value="getSceneNumbering(props.row).season + 'x' + getSceneNumbering(props.row).episode"
                            style="padding: 0; text-align: center; max-width: 60px;"/>
                    </span>
                    
                    <span v-else-if="props.column.field == 'sceneAbsolute'">
                        <input type="text" :placeholder="getSceneAbsoluteNumbering(props.row)" size="6" maxlength="8"
                            class="sceneAbsolute form-control input-scene" :data-for-absolute="props.row.absoluteNumber || 0"
                            :id="'sceneSeasonXEpisode_' + show.id[show.indexer] + props.row.absoluteNumber"
                            title="Change this value if scene absolute numbering differs from the indexer absolute numbering. Generally used for anime shows."
                            :value="getSceneAbsoluteNumbering(props.row) ? getSceneAbsoluteNumbering(props.row) : ''"
                            style="padding: 0; text-align: center; max-width: 60px;"/>
                    </span>

                    <span v-else-if="props.column.field == 'subtitles'">
                        <div v-if="['Archived', 'Downloaded', 'Ignored', 'Skipped'].includes(props.row.status)">
                            <div class="subtitles" v-for="flag in props.row.subtitles" :key="flag">
                                <app-link v-if="flag !== 'und'" class="epRedownloadSubtitle" href="home/searchEpisodeSubtitles?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&season=' + props.row.season + '&episode='props.row.episode' + '&lang=' + flag">
                                    <img :src="'images/subtitles/flags/' + flag + '.png'" width="16" height="11" alt="{flag}" onError="this.onerror=null;this.src='images/flags/unknown.png';"/>
                                </app-link>
                                <img v-if="flag === 'und'" :src="'images/subtitles/flags/' + flag + '.png'" width="16" height="11" alt="flag" onError="this.onerror=null;this.src='images/flags/unknown.png';" />
                            </div>
                        </div>
                    </span>

                    <span v-else-if="props.column.field == 'status'">
                        {{props.row.status}}<quality-pill v-if="props.row.quality !== 0" :quality="props.row.quality"></quality-pill>
                    </span>

                    <span v-else-if="props.column.field == 'search'">
                        <app-link v-if="props.row.season !== 0" :class="retryDownload(props.row) ? 'epRetry' : 'epSearch'" :id="show.indexer + 'x' + show.id[show.indexer] + 'x' + props.row.season + 'x' + props.row.episode" :name="show.indexer + 'x' + show.id[show.indexer] + 'x' + props.row.season + 'x' + props.row.episode" :href="'home/' + (retryDownload(props.row) ? 'retryEpisode' : 'searchEpisode') + '?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&season=' + props.row.season + '&episode=' + props.row.episode"><img data-ep-search src="images/search16.png" height="16" :alt="retryDownload(props.row) ? 'retry' : 'search'" :title="retryDownload(props.row) ? 'Retry Download' : 'Forced Seach'"/></app-link>
                        <app-link class="epManualSearch" :id="show.indexer + 'x' + show.id[show.indexer] + 'x' + props.row.season + 'x' + props.row.episode" :name="show.indexer + 'x' + show.id[show.indexer] + 'x' + props.row.season + 'x' + props.row.episode" :href="'home/snatchSelection?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&season=' + props.row.season + '&episode=' + props.row.episode"><img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search" /></app-link>
                        <img src="images/closed_captioning.png" height="16" alt="search subtitles" title="Search Subtitles" @click="searchSubtitle($event, props.row.season, props.row.episode, props.row.originalIndex)"/>
                    </span>

                    <span v-else>
                        {{props.formattedRow[props.column.field]}}
                    </span>
                </template>

                </vue-good-table>
            </div>
        </div>

        <!--Begin - Bootstrap Modals-->
        <div id="forcedSearchModalFailed" class="modal fade">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                        <h4 class="modal-title">Forced Search</h4>
                    </div>
                    <div class="modal-body">
                        <p>Do you want to mark this episode as failed?</p>
                        <p class="text-warning"><small>The episode release name will be added to the failed history, preventing it to be downloaded again.</small></p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn-medusa btn-danger" data-dismiss="modal">No</button>
                        <button type="button" class="btn-medusa btn-success" data-dismiss="modal">Yes</button>
                    </div>
                </div>
            </div>
        </div>
        <div id="forcedSearchModalQuality" class="modal fade">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                        <h4 class="modal-title">Forced Search</h4>
                    </div>
                    <div class="modal-body">
                        <p>Do you want to include the current episode quality in the search?</p>
                        <p class="text-warning"><small>Choosing No will ignore any releases with the same episode quality as the one currently downloaded/snatched.</small></p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn-medusa btn-danger" data-dismiss="modal">No</button>
                        <button type="button" class="btn-medusa btn-success" data-dismiss="modal">Yes</button>
                    </div>
                </div>
            </div>
        </div>
        <div id="confirmSubtitleReDownloadModal" class="modal fade">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                        <h4 class="modal-title">Re-download subtitle</h4>
                    </div>
                    <div class="modal-body">
                        <p>Do you want to re-download the subtitle for this language?</p>
                        <p class="text-warning"><small>It will overwrite your current subtitle</small></p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn-medusa btn-danger" data-dismiss="modal">No</button>
                        <button type="button" class="btn-medusa btn-success" data-dismiss="modal">Yes</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- TODO: Implement subtitle modal in vue -->
        <!-- <include file="subtitle_modal.mako"/> -->
        <!--End - Bootstrap Modal-->
        <!-- <script type="text/javascript" src="js/rating-tooltip.js?${sbPID}"></script>
        <script type="text/javascript" src="js/ajax-episode-search.js?${sbPID}"></script>
        <script type="text/javascript" src="js/ajax-episode-subtitles.js?${sbPID}"></script> -->
    </div>
</template>

<script>
import formatDate from 'date-fns/format';
import parse from 'date-fns/parse'
import { mapState, mapGetters, mapActions } from 'vuex';
import { apiRoute } from '../api';
import { AppLink, PlotInfo } from './helpers';
import { humanFileSize, attachImdbTooltip } from '../utils';
import { VueGoodTable  } from '../monkeypatched/vue-good-table/vue-good-table.js';
import Backstretch from './backstretch.vue';
import ShowHeader from './show-header.vue';
import SubtitleSearch from './subtitle-search.vue';

export default {
    name: 'show',
    components: {
        AppLink,
        VueGoodTable,
        Backstretch,
        PlotInfo,
        ShowHeader
    },
    metaInfo() {
        if (!this.show || !this.show.title) {
            return {
                title: 'Medusa'
            };
        }
        const { title } = this.show;
        return {
            title,
            titleTemplate: '%s | Medusa'
        };
    },
    props: {
        /**
         * Show indexer
         */
        showIndexer: {
            type: String
        },
        /**
         * Show id
         */
        showId: {
            type: Number
        }
    },
    data() {
        return {
            invertTable: true,
            isMobile: false,
            subtitleSearchComponents: [],
            search: '',
            columns: [{
                label: 'nfo',
                field: 'content.hasNfo',
                type: 'boolean',
                hidden: false
            }, {
                label: 'tbn',
                field: 'content.hasTbn',
                type: 'boolean',
                hidden: false
            }, {
                label: 'Episode',
                field: 'episode',
                type: 'number',
                hidden: false
            }, {
                label: 'Absolute Number',
                field: 'absoluteNumber',
                type: 'number',
                hidden: false
            }, {
                label: 'Scene',
                field: 'scene',
                type: 'number',
                hidden: false
            }, {
                label: 'Scene Absolute',
                field: 'sceneAbsolute',
                type: 'number',
                hidden: false
            }, {
                label: 'Title',
                field: 'title',
                hidden: false
            }, {
                label: 'File',
                field: 'file.location',
                hidden: false
            }, {
                label: 'Size',
                field: 'file.size',
                type: 'number',
                hidden: false
            }, {
                // For now i'm using a custom function the parse it. As the type: date, isn't working for us.
                label: 'Air date',
                field: this.parseDateFn,
                // type: 'date',
                // dateInputFormat: 'YYYY-MM-DD HH:mm:ssZ ', // expects 2018-03-16
                // dateOutputFormat: 'MMM Do YYYY', // outputs Mar 16th 2018
                hidden: false
            }, {
                label: 'Download',
                field: 'download',
                hidden: false
            }, {
                label: 'Subtitles',
                field: 'subtitles',
                sortable: false,
                hidden: false
            }, {
                label: 'Status',
                field: 'status',
                hidden: false
            }, {
                label: 'Search',
                field: 'search',
                hidden: false
            }],
            selectedEpisodes: []
        };
    },
    computed: {
        ...mapState({
            shows: state => state.shows.shows,
            configLoaded: state => state.config.fanartBackground !== null,
            config: state => state.config            
        }),
        ...mapGetters({
            getShowById: 'getShowById',
            show: 'getCurrentShow'
        }),
        indexer() {
            return this.showIndexer || this.$route.query.indexername;
        },
        id() {
            return this.showId || Number(this.$route.query.seriesid) || undefined;
        },
        seasonsInverse() {
            const { invertTable, show } = this;
            const { seasons } = show;
            if (!seasons) {
                return [];
            }
            
            if (invertTable) {
                return this.show.seasons.slice().reverse();
            } else {
                return this.show.seasons;
            }
        }
    },
    created() {
        const { getShows } = this;
        // Needed for the show-selector component
        getShows();
    },
    mounted() {
        const {
            id,
            indexer,
            getShow,
            setEpisodeSceneNumbering,
            setAbsoluteSceneNumbering,
            setInputValidInvalid,
            getSeasonSceneExceptions,
            $store,
            show
        } = this;

        // Let's tell the store which show we currently want as current.
        $store.commit('currentShow', {
            indexer,
            id
        });

        // We need detailed info for the seasons, so let's get it.
        if (!show || !show.seasons) {
            getShow({ id, indexer, detailed: true });
        }

        this.$watch('show', () => {
            this.$nextTick(() => this.reflowLayout());
        });

        ['load', 'resize'].map(event => {
            return window.addEventListener(event, () => {
                this.reflowLayout();
            });
        });

        window.addEventListener('load', () => {
            $.ajaxEpSearch({
                colorRow: true
            });

            startAjaxEpisodeSubtitles(); // eslint-disable-line no-undef
            $.ajaxEpSubtitlesSearch();
            $.ajaxEpRedownloadSubtitle();
        });

        $(document.body).on('click', '.seasonCheck', event => {
            const seasCheck = event.currentTarget;
            const seasNo = $(seasCheck).attr('id');

            $('#collapseSeason-' + seasNo).collapse('show');
            const seasonIdentifier = 's' + seasNo;
            $('.epCheck:visible').each((index, element) => {
                const epParts = $(element).attr('id').split('e');
                if (epParts[0] === seasonIdentifier) {
                    element.checked = seasCheck.checked;
                }
            });
        });

        let lastCheck = null;
        $(document.body).on('click', '.epCheck', event => {
            const target = event.currentTarget;
            if (!lastCheck || !event.shiftKey) {
                lastCheck = target;
                return;
            }

            const check = target;
            let found = 0;

            $('.epCheck').each((index, element) => {
                if (found === 1) {
                    element.checked = lastCheck.checked;
                }

                if (found === 2) {
                    return false;
                }

                if (element === check || element === lastCheck) {
                    found++;
                }
            });
        });

        // Initially show/hide all the rows according to the checkboxes
        $('#checkboxControls input').each((index, element) => {
            const status = $(element).prop('checked');
            $('tr.' + $(element).attr('id')).each((index, tableRow) => {
                if (status) {
                    $(tableRow).show();
                } else {
                    $(tableRow).hide();
                }
            });
        });

        $(document.body).on('change', '.sceneSeasonXEpisode', event => {
            const target = event.currentTarget;
            // Strip non-numeric characters
            const value = $(target).val();
            $(target).val(value.replace(/[^0-9xX]*/g, ''));
            const forSeason = $(target).attr('data-for-season');
            const forEpisode = $(target).attr('data-for-episode');

            // If empty reset the field
            if (value === '') {
                setEpisodeSceneNumbering(forSeason, forEpisode, null, null);
                return;
            }

            const m = $(target).val().match(/^(\d+)x(\d+)$/i);
            const onlyEpisode = $(target).val().match(/^(\d+)$/i);
            let sceneSeason = null;
            let sceneEpisode = null;
            let isValid = false;
            if (m) {
                sceneSeason = m[1];
                sceneEpisode = m[2];
                isValid = setInputValidInvalid(true, $(target));
            } else if (onlyEpisode) {
                // For example when '5' is filled in instead of '1x5', asume it's the first season
                sceneSeason = forSeason;
                sceneEpisode = onlyEpisode[1];
                isValid = setInputValidInvalid(true, $(target));
            } else {
                isValid = setInputValidInvalid(false, $(target));
            }

            if (isValid) {
                setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode);
            }
        });

        $(document.body).on('change', '.sceneAbsolute', event => {
            const target = event.currentTarget;
            // Strip non-numeric characters
            $(target).val($(target).val().replace(/[^0-9xX]*/g, ''));
            const forAbsolute = $(target).attr('data-for-absolute');

            const m = $(target).val().match(/^(\d{1,3})$/i);
            let sceneAbsolute = null;
            if (m) {
                sceneAbsolute = m[1];
            }
            setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute);
        });

        // Changes the button when clicked for collapsing/expanding the season to show/hide episodes
        document.querySelectorAll('.collapse.toggle').forEach(element => {
            element.addEventListener('hide.bs.collapse', () => {
                // On hide
                const reg = /collapseSeason-(\d+)/g;
                const result = reg.exec(this.id);
                $('#showseason-' + result[1]).text('Show Episodes');
                $('#season-' + result[1] + '-cols').addClass('shadow');
            });
            element.addEventListener('show.bs.collapse', () => {
                // On show
                const reg = /collapseSeason-(\d+)/g;
                const result = reg.exec(this.id);
                $('#showseason-' + result[1]).text('Hide Episodes');
                $('#season-' + result[1] + '-cols').removeClass('shadow');
            });
        });

        // Get the season exceptions and the xem season mappings.
        // getSeasonSceneExceptions();
    },
    methods: {
        humanFileSize,
        ...mapActions({
            getShow: 'getShow', // Map `this.getShow()` to `this.$store.dispatch('getShow')`
            getShows: 'getShows' 
        }),
        statusQualityUpdate(event) {
            const { selectedEpisodes, setStatus, setQuality } = this;

            if (event.newQuality !== null) {
                setQuality(event.newQuality, selectedEpisodes);
            }
            if (event.newStatus !== null) {
                setStatus(event.newStatus, selectedEpisodes);
            } 
        },
        setQuality(quality, episodes) {
            const { id, indexer, getShow, show } = this;
            const patchData = {};

            episodes.forEach(episode => {
                patchData[episode.identifier] = { quality: parseInt(quality, 10) };
            });

            api.patch('series/' + show.id.slug + '/episodes', patchData)
            .then(response => {
                console.info(`patched show ${show.id.slug} with quality ${quality}`);
                getShow({ id, indexer, detailed: true });
            }).catch(error => {
                console.error(String(error));
            });
        },
        setStatus(status, episodes) {
            const { id, indexer, getShow, show } = this;
            const patchData = {};

            episodes.forEach(episode => {
                patchData[episode.identifier] = { status };
            });

            api.patch('series/' + show.id.slug + '/episodes', patchData)
            .then(response => {
                console.info(`patched show ${show.id.slug} with status ${status}`);
                getShow({ id, indexer, detailed: true });
            }).catch(error => {
                console.error(String(error));
            });
        },
        parseDateFn(row) {
            return formatDate(parse(row.airDate), 'DD/MM/YYYY, hh:mm a');
        },
        parseSubtitlesFn(row) {
        },
        rowStyleClassFn(row) {
            return row.status.toLowerCase().trim();
        },
        searchSubtitle(event, season, episode, rowIndex) {
            const { id, indexer, getShow, show, subtitleSearchComponents } = this;
            const SubtitleSearchClass = Vue.extend(SubtitleSearch);
            const instance = new SubtitleSearchClass({
                propsData: { show, season, episode, key: rowIndex },
                parent: this
            });

            // Update the show, as we downloaded new subtitle(s)
            instance.$on('update', event => {
                // TODO: This could be replaced by the generic websocket updates in future. 
                if (event.reason === 'new subtitles found') {
                    getShow({ id, indexer, detailed: true });
                }
            });

            const node = document.createElement('div')
            this.$refs['table-seasons'].$refs[`row-${rowIndex}`][0].after(node)
            instance.$mount(node) // pass nothing
            subtitleSearchComponents.push(instance);
        },
        /**
         * Attaches IMDB tooltip,
         * Moves summary and checkbox controls backgrounds
         */
        reflowLayout() {
            console.debug('Reflowing layout');

            this.$nextTick(() => {
                this.moveSummaryBackground();
                this.movecheckboxControlsBackground();
            });

            attachImdbTooltip(); // eslint-disable-line no-undef
        },
        /**
         * Adjust the summary background position and size on page load and resize
         */
        moveSummaryBackground() {
            const height = $('#summary').height() + 10;
            const top = $('#summary').offset().top + 5;

            $('#summaryBackground').height(height);
            $('#summaryBackground').offset({ top, left: 0 });
            $('#summaryBackground').show();
        },
        /**
         * Adjust the checkbox controls (episode filter) background position
         */
        movecheckboxControlsBackground() {
            const height = $('#checkboxControls').height() + 10;
            const top = $('#checkboxControls').offset().top - 3;

            $('#checkboxControlsBackground').height(height);
            $('#checkboxControlsBackground').offset({ top, left: 0 });
            $('#checkboxControlsBackground').show();
        },
        setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode) {
            const indexerName = $('#indexer-name').val();
            const seriesId = $('#series-id').val();

            if (sceneSeason === '') {
                sceneSeason = null;
            }
            if (sceneEpisode === '') {
                sceneEpisode = null;
            }

            $.getJSON('home/setSceneNumbering', {
                indexername: indexerName,
                seriesid: seriesId,
                forSeason,
                forEpisode,
                sceneSeason,
                sceneEpisode
            }, data => {
                // Set the values we get back
                if (data.sceneSeason === null || data.sceneEpisode === null) {
                    $('#sceneSeasonXEpisode_' + seriesId + '_' + forSeason + '_' + forEpisode).val('');
                } else {
                    $('#sceneSeasonXEpisode_' + seriesId + '_' + forSeason + '_' + forEpisode).val(data.sceneSeason + 'x' + data.sceneEpisode);
                }
                if (!data.success) {
                    if (data.errorMessage) {
                        alert(data.errorMessage); // eslint-disable-line no-alert
                    } else {
                        alert('Update failed.'); // eslint-disable-line no-alert
                    }
                }
            });
        },
        setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute) {
            const indexerName = $('#indexer-name').val();
            const seriesId = $('#series-id').val();

            if (sceneAbsolute === '') {
                sceneAbsolute = null;
            }

            $.getJSON('home/setSceneNumbering', {
                indexername: indexerName,
                seriesid: seriesId,
                forAbsolute,
                sceneAbsolute
            }, data => {
                // Set the values we get back
                if (data.sceneAbsolute === null) {
                    $('#sceneAbsolute_' + seriesId + '_' + forAbsolute).val('');
                } else {
                    $('#sceneAbsolute_' + seriesId + '_' + forAbsolute).val(data.sceneAbsolute);
                }

                if (!data.success) {
                    if (data.errorMessage) {
                        alert(data.errorMessage); // eslint-disable-line no-alert
                    } else {
                        alert('Update failed.'); // eslint-disable-line no-alert
                    }
                }
            });
        },
        setInputValidInvalid(valid, el) {
            if (valid) {
                $(el).css({
                    'background-color': '#90EE90', // Green
                    'color': '#FFF', // eslint-disable-line quote-props
                    'font-weight': 'bold'
                });
                return true;
            }
            $(el).css({
                'background-color': '#FF0000', // Red
                'color': '#FFF!important', // eslint-disable-line quote-props
                'font-weight': 'bold'
            });
            return false;
        },
        /**
         * Check if any of the episodes in this season does not have the status "unaired".
         * If that's the case we want to manual season search icon.
         */
        anyEpisodeNotUnaired(season) {
            return season.episodes.filter(ep => ep.status !== 'Unaired').length > 0;
        },
        episodesInverse(season) {
            const { invertTable } = this;
            if (!season.episodes) {
                return [];
            }
            if (invertTable) {
                return season.episodes.slice().reverse();
            } else {
                return season.episodes;
            }
        },
        /**
         * Check if the season/episode combination exists in the scene numbering.
         */
        getSceneNumbering(episode) {
            const { show } = this;
            const { xemNumbering } = show;

            if (xemNumbering.length !== 0) {
                const mapped = xemNumbering.filter(x => {
                    return x.source.season === episode.season && x.source.episode === episode.episode;
                });
                if (mapped.length !== 0) {
                    return mapped[0].destination;
                }
            }
            return { season: 0, episode: 0 };
        },
        getSceneAbsoluteNumbering(episode) {
            const { show } = this;
            const { sceneAbsoluteNumbering, xemAbsoluteNumbering } = show;
            const xemAbsolute = xemAbsoluteNumbering[episode.absoluteNumber];

            if (Object.keys(sceneAbsoluteNumbering).length > 0) {
                return sceneAbsoluteNumbering[episode.absoluteNumber];
            } else if (xemAbsolute) {
                return xemAbsolute;
            }
            return 0;
        },
        retryDownload(episode) {
            const { config } = this;
            return (config.failedDownloads.enabled && ['Snatched', 'Snatched (Proper)', 'Snatched (Best)', 'Downloaded'].includes(episode.status));
        },
        showSubtitleButton(episode) {
            const { config, show } = this;
            return (episode.season !== 0 && config.subtitles.enabled && show.config.subtitlesEnabled && !['Snatched', 'Snatched (Proper)', 'Snatched (Best)', 'Downloaded'].includes(episode.status));
        },
        totalSeasonEpisodeSize(season) {
            return season.episodes.filter(x => x.file && x.file.size > 0).reduce((a, b) => a + b.file.size, 0);
        },
        getSeasonExceptions(season) {
            const { show } = this;
            const { allSceneExceptions } = show;
            let bindData = { class: 'display: none' };

            // Map the indexer season to a xem mapped season.
            // check if the season exception also exists in the xem numbering table

            let xemSeasons = [];
            let foundInXem = false;
            if (show.xemNumbering.length > 0) {
                const xemResult = show.xemNumbering.filter(x => x.source.season === season);
                // Create an array with unique seasons
                xemSeasons = [...new Set(xemResult.map(item => item.destination.season))];
                foundInXem = Boolean(xemSeasons.length);
            }

            // Check if there is a season exception for this season
            if (allSceneExceptions[season]) {
                // if there is not a match on the xem table, display it as a medusa scene exception
                bindData = {
                    id: `xem-exception-season-${foundInXem ? xemSeasons[0] : season}`,
                    alt: foundInXem ? '[xem]' : '[medusa]',
                    src: foundInXem ? 'images/xem.png' : 'images/ico/favicon-16.png',
                    title: xemSeasons.reduce(function (a, b) {
                        return a = a.concat(allSceneExceptions[b]);
                    }, []).join(', '),
                }
            }

            return bindData;
        },
        /**
         * Sort all season tables, when a sort event is emitted.
         */
        episodeTableSorted(event) {
            const { show } = this;
            show.seasons.forEach(season => {
                this.$refs[`episodeTable-${season.season}`].$refs[`tableSeason-${season.season}`].setOrder(event.column, event.ascending)
            });
        },
        toggleColumn(index, event) {
            // Set hidden to inverse of what it currently is
            this.$set( this.columns[ index ], 'hidden', ! this.columns[ index ].hidden );
        }
    }
};
</script>

<style scope>
.vgt-global-search__input.vgt-pull-left {
    /* width: 50%; */
    /* display: inline-block; */
    float: left;
}
.vgt-input {
    border: 1px solid #ccc;
    transition: border-color .15s ease-in-out,box-shadow .15s ease-in-out,-webkit-box-shadow .15s ease-in-out;
    height: 30px;
    padding: 5px 10px;
    font-size: 12px;
    line-height: 1.5;
    border-radius: 3px;
}
div.vgt-responsive > table tbody > tr > th.vgt-row-header > span {
    font-size: 24px;
    margin-top: 20px;
    margin-bottom: 10px;
}
.fanartBackground.displayShow {
    clear: both;
    opacity: 0.9;
}
.defaultTable.displayShow {
    clear: both;
}
.displayShowTable.displayShow {
    clear: both;
}
.fanartBackground table {
    table-layout: auto;
    width: 100%;
    border-collapse: collapse;
    border-spacing: 0;
    text-align: center;
    border: none;
    empty-cells: show;
    color: rgb(0, 0, 0) !important;
}
.summaryFanArt {
    opacity: 0.9;
}
.fanartBackground > table th.vgt-row-header {
    border: none !important;
    background-color: transparent !important;
    color: rgb(255, 255, 255) !important;
    padding-top: 15px !important;
    text-align: left !important;
}
.fanartBackground td.col-search {
    text-align: center;
}

/* Trying to migrate this from tablesorter */
/* =======================================================================
tablesorter.css
========================================================================== */

.vgt-table {
    width: 100%;
    margin-right: auto;
    margin-left: auto;
    color: rgb(0, 0, 0);
    text-align: left;
    /* background-color: rgb(255, 255, 255); */
    border-spacing: 0;
}

.vgt-table th,
.vgt-table td {
    padding: 4px;
    border-top: rgb(34, 34, 34) 1px solid;
    border-left: rgb(34, 34, 34) 1px solid;
    vertical-align: middle;
}

/* remove extra border from left edge */
.vgt-table th:first-child,
.vgt-table td:first-child {
    border-left: none;
}

.vgt-table th {
    /* color: rgb(255, 255, 255); */
    text-align: center;
    text-shadow: -1px -1px 0 rgba(0, 0, 0, 0.3);
    background-color: rgb(51, 51, 51);
    border-collapse: collapse;
    font-weight: normal;
    white-space: nowrap;
    color: rgb(255, 255, 255);
}

/* .vgt-table .tablesorter-header {
    padding: 4px 18px;
    cursor: pointer;
    background-image: url(data:image/gif;base64,R0lGODlhFQAJAIAAAP///////yH5BAEAAAEALAAAAAAVAAkAAAIXjI+AywnaYnhUMoqt3gZXPmVg94yJVQAAOw==);
    background-position: center right;
    background-repeat: no-repeat;
} */

.vgt-table thead th.sorting.sorting-desc {
    background-color: rgb(85, 85, 85);
    background-image: url(data:image/gif;base64,R0lGODlhFQAEAIAAAP///////yH5BAEAAAEALAAAAAAVAAQAAAINjB+gC+jP2ptn0WskLQA7);
}

.vgt-table thead th.sorting.sorting-asc {
    background-color: rgb(85, 85, 85);
    background-image: url(data:image/gif;base64,R0lGODlhFQAEAIAAAP///////yH5BAEAAAEALAAAAAAVAAQAAAINjI8Bya2wnINUMopZAQA7);
    background-position-x: right;
    background-position-y: bottom;
}

.vgt-table thead th.sorting {
    background-repeat: no-repeat;
}

.vgt-table thead th {
    background-image: none;
    padding: 4px;
    cursor: default;
}

/* thead.tablesorter-stickyHeader {
    border-top: 2px solid rgb(255, 255, 255);
    border-bottom: 2px solid rgb(255, 255, 255);
} */

/* Zebra Widget - row alternating colors */
.vgt-table tr:nth-child(odd) {
    /* background-color: rgb(245, 241, 228); */
}

.vgt-table tr:nth-child(odd) {
    /* background-color: rgb(223, 218, 207); */
}

/* filter widget */
/* .tablesorter .filtered {
    display: none;
} */

.vgt-table input.tablesorter-filter {
    width: 98%;
    height: auto;
    -webkit-box-sizing: border-box;
    -moz-box-sizing: border-box;
    box-sizing: border-box;
}

.vgt-table tr.tablesorter-filter-row,
.vgt-table tr.tablesorter-filter-row td {
    text-align: center;
    /* background: rgb(238, 238, 238); */
    /* border-bottom: 1px solid rgb(221, 221, 221); */
}

/* optional disabled input styling */
.vgt-table input.tablesorter-filter-row .disabled {
    display: none;
}

.tablesorter-header-inner {
    padding: 0 2px;
    text-align: center;
}

.vgt-table tfoot tr {
    color: rgb(255, 255, 255);
    text-align: center;
    text-shadow: -1px -1px 0 rgba(0, 0, 0, 0.3);
    background-color: rgb(51, 51, 51);
    border-collapse: collapse;
}

.vgt-table tfoot a {
    color: rgb(255, 255, 255);
    text-decoration: none;
}

.vgt-table th.vgt-row-header {
    text-align: left;
}

.vgt-table .season-header {
    display: inline;
    margin-left: 5px;
}

.vgt-table tr.spacer {
    height: 25px;
}

</style>


// window.app = {};
// window.app = new Vue({
//     el: '#vue-wrap',
//     store,
//     router,
//     data() {
//         return {
//             // This loads show.vue
//             pageComponent: 'show'
//         }
//     },
//     created() {
//         const { $store } = this;
//         // Needed for the show-selector component
//         $store.dispatch('getShows');
//     }
// });
// </script>
