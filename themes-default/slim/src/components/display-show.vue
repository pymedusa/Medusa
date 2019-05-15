<template>
    <div class="display-show-template" :class="theme">
        <vue-snotify></vue-snotify>
        <backstretch v-if="config.fanartBackground" v-bind="{indexer, id}"></backstretch>
        <input type="hidden" id="series-id" value="" />
        <input type="hidden" id="indexer-name" value="" />
        <input type="hidden" id="series-slug" value="" />

        <show-header @reflow="reflowLayout" type="show"
            :show-id="id" :show-indexer="indexer" @update="statusQualityUpdate"
        ></show-header>

        <!-- <subtitle-search v-if="Boolean(show)" :show="show" :season="4" :episode="8"></subtitle-search> -->

        <div class="row">
            <div class="col-md-12 top-15 displayShow horizontal-scroll" :class="{ fanartBackground: config.fanartBackground }">
                <vue-good-table v-if="show.seasons"
                :columns="columns"
                :rows="show.seasons.slice().reverse()"
                :groupOptions="{
                    enabled: true,
                    mode: 'span',
                    customChildObject: 'episodes'
                }"
                :pagination-options="{
                    enabled: true,
                    perPage: paginationPerPage,
                    perPageDropdown: [25, 50, 100, 250, 500]
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
                    selectionText: 'episodes selected',
                    clearSelectionText: 'clear',
                    selectAllByGroup: true
                }"
                :row-style-class="rowStyleClassFn"
                ref="table-seasons"
                @on-selected-rows-change="selectedEpisodes=$event.selectedRows" 
                @on-per-page-change="paginationPerPage=$event.currentPerPage">
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

                <template slot="table-header-row" slot-scope="props">
                    <h3 class="season-header toggle collapse"><app-link :name="'season-'+ props.row.season"></app-link>
                        <!-- {'Season ' + str(epResult['season']) if int(epResult['season']) > 0 else 'Specials'} -->
                        {{ props.row.label > 0 ? 'Season ' + props.row.label : 'Specials' }}
                        <!-- Only show the search manual season search, when any of the episodes in it is not unaired -->
                        <app-link v-if="anyEpisodeNotUnaired(props.row)" class="epManualSearch" :href="'home/snatchSelection?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&amp;season=' + props.row.season + '&amp;episode=1&amp;manual_search_type=season'">
                            <img v-if="config" data-ep-manual-search src="images/manualsearch-white.png" width="16" height="16" alt="search" title="Manual Search" />
                        </app-link>
                        <div class="season-scene-exception" :data-season="props.row.season > 0 ? props.row.season : 'Specials'"></div>
                    </h3>
                </template>

                <template slot="table-footer-row" slot-scope="{headerRow}">
                    <tr colspan="9999" :id="`season-${headerRow.season}-footer`" class="seasoncols border-bottom shadow">
                        <th class="col-footer" colspan=15 align=left>Season contains {{headerRow.episodes.length}} episodes with total filesize: {{addFileSize(headerRow)}}</th>
                    </tr>
                    <tr class="spacer"></tr>
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
                        <span :title="props.row.file.location !== '' ? props.row.file.location : ''" :class="{addQTip: props.row.file.location !== ''}">{{props.row.episode}}</span>
                    </span>

                    <span v-else-if="props.column.label == 'Scene'">
                            <input type="text" :placeholder="props.formattedRow[props.column.field].season + 'x' + props.formattedRow[props.column.field].episode" size="6" maxlength="8"
                                class="sceneSeasonXEpisode form-control input-scene addQTip" :data-for-season="props.row.season" :data-for-episode="props.row.episode"
                                :id="'sceneSeasonXEpisode_' + show.id[show.indexer] + '_' + props.row.season + '_' + props.row.episode"
                                title="Change this value if scene numbering differs from the indexer episode numbering. Generally used for non-anime shows."
                                :value="props.formattedRow[props.column.field].season + 'x' + props.formattedRow[props.column.field].episode"
                                style="padding: 0; text-align: center; max-width: 60px;"/>
                    </span>

                    <span v-else-if="props.column.label == 'Scene Absolute'">
                        <input type="text" :placeholder="props.formattedRow[props.column.field]" size="6" maxlength="8"
                            class="sceneAbsolute form-control input-scene addQTip" :data-for-absolute="props.row.absoluteNumber || 0"
                            :id="'sceneSeasonXEpisode_' + show.id[show.indexer] + props.row.absoluteNumber"
                            title="Change this value if scene absolute numbering differs from the indexer absolute numbering. Generally used for anime shows."
                            :value="props.formattedRow[props.column.field] ? props.formattedRow[props.column.field] : ''"
                            style="padding: 0; text-align: center; max-width: 60px;"/>
                    </span>

                    <span v-else-if="props.column.field == 'title'">
                        <plot-info v-if="props.row.description !== ''" :description="props.row.description" :show-slug="show.id.slug" :season="props.row.season" :episode="props.row.episode"></plot-info>
                        {{props.row.title}}
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
                        {{props.row.status}} <quality-pill v-if="props.row.quality !== 0" :quality="props.row.quality"></quality-pill>
                        <img :title="props.row.watched ? 'This episode has been flagged as watched' : ''" class="addQTip" v-if="props.row.status !== 'Unaired'" :src="`images/${props.row.watched ? '' : 'not'}watched.png`" width="16" @click="updateEpisodeWatched(props.row, !props.row.watched);"/>
                    </span>

                    <span v-else-if="props.column.field == 'search'">
                        <img class="epForcedSearch" :id="show.indexer + 'x' + show.id[show.indexer] + 'x' + props.row.season + 'x' + props.row.episode" :name="show.indexer + 'x' + show.id[show.indexer] + 'x' + props.row.season + 'x' + props.row.episode" :ref="`search-${props.row.slug}`" src="images/search16.png" height="16" :alt="retryDownload(props.row) ? 'retry' : 'search'" :title="retryDownload(props.row) ? 'Retry Download' : 'Forced Seach'" @click="queueSearch(props.row)"/>
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

        <modal name="query-start-backlog-search" :height="'auto'" :width="'80%'">
            <transition name="modal">
                <div class="modal-mask">
                    <div class="modal-wrapper">
                        <div class="modal-content">
                            <div class="modal-header">
                                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                                <h4 class="modal-title">Start search?</h4>
                            </div>
                            <div class="modal-body">
                                <p>Some episodes have been changed to 'Wanted'. Do you want to trigger a backlog search?</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn-medusa btn-danger" data-dismiss="modal" @click="$modal.hide('query-start-backlog-search')">No</button>
                                <button type="button" class="btn-medusa btn-success" data-dismiss="modal" @click="queueSearch(null); $modal.hide('query-start-backlog-search')">Yes</button>
                            </div>
                        </div>
                    </div>
                </div>
            </transition>
        </modal>

        <modal name="query-mark-failed-and-search" @before-open="beforeFailedSearchModalClose" :height="'auto'" :width="'80%'">
            <transition name="modal">
                <div class="modal-mask">
                    <div class="modal-wrapper">
                        <div class="modal-content">
                            <div class="modal-header">
                                Mark episode as failed and search?
                            </div>

                            <div class="modal-body">
                                <p>Starting to search for the episode</p>
                                <p v-if="searchedEpisode">Would you also like to mark episode {{searchedEpisode.slug}} as "failed"? This will make sure the episode cannot be downloaded again</p>
                            </div>

                            <div class="modal-footer">
                                <button type="button" class="btn-medusa btn-danger" data-dismiss="modal" @click="forcedSearch(searchedEpisode, 'backlog'); $modal.hide('query-mark-failed-and-search')">No</button>
                                <button type="button" class="btn-medusa btn-success" data-dismiss="modal" @click="forcedSearch(searchedEpisode, 'failed'); $modal.hide('query-mark-failed-and-search')">Yes</button>
                                <button type="button" class="btn-medusa btn-danger" data-dismiss="modal" @click="$modal.hide('query-mark-failed-and-search')">Cancel</button>
                            </div>
                        </div>
                    </div>
                </div>
            </transition>
        </modal>

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
import { AppLink, PlotInfo } from './helpers';
import { humanFileSize, mapDateFormat } from '../utils';
import { addQTip, updateSearchIcons } from '../jquery-wrappers';
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
        const { getCookie } = this;
        return {
            invertTable: true,
            isMobile: false,
            subtitleSearchComponents: [],
            search: '',
            columns: [{
                label: 'NFO',
                field: 'content.hasNfo',
                type: 'boolean',
                sortable: false,
                hidden: getCookie('displayShow-hide-field-NFO')
            }, {
                label: 'TBN',
                field: 'content.hasTbn',
                type: 'boolean',
                sortable: false,
                hidden: getCookie('displayShow-hide-field-TBN')
            }, {
                label: 'Episode',
                field: 'episode',
                type: 'number',
                hidden: getCookie('displayShow-hide-field-Episode')
            }, {
                label: 'Absolute Number',
                field: 'absoluteNumber',
                type: 'number',
                hidden: getCookie('displayShow-hide-field-Absolute Number')
            }, {
                label: 'Scene',
                field: row => {
                    const { getSceneNumbering } = this;
                    return getSceneNumbering(row);
                },
                sortable: false,
                hidden: getCookie('displayShow-hide-field-Scene')
            }, {
                label: 'Scene Absolute',
                field: row => {
                    const { getSceneAbsoluteNumbering } = this;
                    return getSceneAbsoluteNumbering(row);
                },
                type: 'number',
                /**
                 * Vue-good-table sort overwrite function.
                 * @param {Object} x - row1 value for column.
                 * @param {object} y - row2 value for column.
                 * @returns {Boolean} - if we want to display this row before the next
                 */
                sortFn(x, y) {
                    return (x < y ? -1 : (x > y ? 1 : 0));
                },
                hidden: getCookie('displayShow-hide-field-Scene Absolute')
            }, {
                label: 'Title',
                field: 'title',
                hidden: getCookie('displayShow-hide-field-Title')
            }, {
                label: 'File',
                field: 'file.location',
                hidden: getCookie('displayShow-hide-field-File')
            }, {
                label: 'Size',
                field: 'file.size',
                type: 'number',
                formatFn: humanFileSize,
                hidden: getCookie('displayShow-hide-field-Size')
            }, {
                // For now i'm using a custom function the parse it. As the type: date, isn't working for us.
                // But the goal is to have this user formatted (as configured in backend)
                label: 'Air date',
                field: this.parseDateFn,
                hidden: getCookie('displayShow-hide-field-Air date')
            }, {
                label: 'Download',
                field: 'download',
                sortable: false,
                hidden: getCookie('displayShow-hide-field-Download')
            }, {
                label: 'Subtitles',
                field: 'subtitles',
                sortable: false,
                hidden: getCookie('displayShow-hide-field-Subtitles')
            }, {
                label: 'Status',
                field: 'status',
                hidden: getCookie('displayShow-hide-field-Status')
            }, {
                label: 'Search',
                field: 'search',
                sortable: false,
                hidden: getCookie('displayShow-hide-field-Search')
            }],
            paginationPerPage: getCookie('displayShow-pagination-perPage') || 50,
            selectedEpisodes: [],
            // We need to keep track of which episode where trying to search, for the vue-modal
            searchedEpisode: null
        };
    },
    computed: {
        ...mapState({
            shows: state => state.shows.shows,
            configLoaded: state => state.config.fanartBackground !== null,
            config: state => state.config
        }),
        ...mapGetters({
            show: 'getCurrentShow',
            getOverviewStatus: 'getOverviewStatus'
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
            }

            return this.show.seasons;
        },
        theme() {
            const { config } = this;
            const { themeName } = config;
            return themeName || 'light';
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
                patchData[episode.slug] = { quality: parseInt(quality, 10) };
            });

            api.patch('series/' + show.id.slug + '/episodes', patchData) // eslint-disable-line no-undef
                .then( _ => {
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
                patchData[episode.slug] = { status };
            });

            api.patch('series/' + show.id.slug + '/episodes', patchData) // eslint-disable-line no-undef
                .then( _ => {
                    console.info(`patched show ${show.id.slug} with status ${status}`);
                    getShow({ id, indexer, detailed: true });
                }).catch(error => {
                    console.error(String(error));
                });

            if (status === 3) {
                this.$modal.show('query-start-backlog-search');
            }
        },
        parseDateFn(row) {
            const { config } = this;
            if (config.datePreset === '%x') {
                return new Date(row.airDate).toLocaleString();
            }

            return formatDate(parse(row.airDate), mapDateFormat(`${config.datePreset} ${config.timePreset}`));
        },
        rowStyleClassFn(row) {
            const { getOverviewStatus, show } = this;
            return getOverviewStatus(row.status, row.quality, show.config.qualities).toLowerCase().trim();
        },
        /**
         * Add (reduce) the total episodes filesize.
         * @param {object} headerRow header row object.
         * @returns {string} - Human readable file size.
         */
        addFileSize(headerRow) {
            return humanFileSize(headerRow.episodes.reduce((a, b) => a + (b.file.size || 0), 0));
        },
        searchSubtitle(event, season, episode, rowIndex) {
            const { id, indexer, getShow, show, subtitleSearchComponents } = this;
            const SubtitleSearchClass = Vue.extend(SubtitleSearch);  // eslint-disable-line no-undef
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

            const node = document.createElement('div');
            this.$refs['table-seasons'].$refs[`row-${rowIndex}`][0].after(node);
            instance.$mount(node);
            subtitleSearchComponents.push(instance);
        },
        /**
         * Attaches IMDB tooltip,
         * Moves summary and checkbox controls backgrounds
         */
        reflowLayout() {
            console.debug('Reflowing layout');

            this.$nextTick(() => {
                this.movecheckboxControlsBackground();
            });
            addQTip(); // eslint-disable-line no-undef
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
            const { $snotify, id, indexer, show } = this;

            if (!show.config.scene) {
                $snotify.warning(
                    'To change episode scene numbering you need to enable the show option `scene` first',
                    'Warning',
                    { timeout: 0 }
                );
            }

            if (sceneSeason === '') {
                sceneSeason = null;
            }

            if (sceneEpisode === '') {
                sceneEpisode = null;
            }

            $.getJSON('home/setSceneNumbering', {
                indexername: indexer,
                seriesid: id,
                forSeason,
                forEpisode,
                sceneSeason,
                sceneEpisode
            }, data => {
                // Set the values we get back
                if (data.sceneSeason === null || data.sceneEpisode === null) {
                    $('#sceneSeasonXEpisode_' + id + '_' + forSeason + '_' + forEpisode).val('');
                } else {
                    $('#sceneSeasonXEpisode_' + id + '_' + forSeason + '_' + forEpisode).val(data.sceneSeason + 'x' + data.sceneEpisode);
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
            const { $snotify, id, indexer, show } = this;

            if (!show.config.scene) {
                $snotify.warning(
                    'To change an anime episode scene numbering you need to enable the show option `scene` first',
                    'Warning',
                    { timeout: 0 }
                );
            }

            if (sceneAbsolute === '') {
                sceneAbsolute = null;
            }

            $.getJSON('home/setSceneNumbering', {
                indexername: indexer,
                seriesid: id,
                forAbsolute,
                sceneAbsolute
            }, data => {
                // Set the values we get back
                if (data.sceneAbsolute === null) {
                    $('#sceneAbsolute_' + id + '_' + forAbsolute).val('');
                } else {
                    $('#sceneAbsolute_' + id + '_' + forAbsolute).val(data.sceneAbsolute);
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
            }

            return season.episodes;
        },
        /**
         * Check if the season/episode combination exists in the scene numbering.
         * @param {Object} episode - object.
         * @returns {Object} with scene season and episodes mapped numbering.
         */
        getSceneNumbering(episode) {
            const { show } = this;
            const { sceneNumbering, xemNumbering } = show;

            if (!show.config.scene) {
                return { season: 0, episode: 0 };
            }

            // Manually configured scene numbering
            if (sceneNumbering.length !== 0) {
                const mapped = sceneNumbering.filter(x => {
                    return x.source.season === episode.season && x.source.episode === episode.episode;
                });
                if (mapped.length !== 0) {
                    return mapped[0].destination;
                }
            }

            // Scene numbering downloaded from thexem.de.
            if (xemNumbering.length !== 0) {
                const mapped = xemNumbering.filter(x => {
                    return x.source.season === episode.season && x.source.episode === episode.episode;
                });
                if (mapped.length !== 0) {
                    return mapped[0].destination;
                }
            }

            return { season: episode.scene.season || 0, episode: episode.scene.episode || 0 };
        },
        getSceneAbsoluteNumbering(episode) {
            const { show } = this;
            const { sceneAbsoluteNumbering, xemAbsoluteNumbering } = show;

            if (!show.config.anime || !show.config.scene) {
                return episode.scene.absoluteNumber;
            }

            if (Object.keys(sceneAbsoluteNumbering).length > 0 && sceneAbsoluteNumbering[episode.absoluteNumber]) {
                return sceneAbsoluteNumbering[episode.absoluteNumber];
            }

            if (Object.keys(xemAbsoluteNumbering).length > 0 && xemAbsoluteNumbering[episode.absoluteNumber]) {
                return xemAbsoluteNumbering[episode.absoluteNumber];
            }

            return episode.scene.absoluteNumber;
        },
        /**
         * Vue-js-modal requires a method, to pass an event to.
         * The event then can be used to assign the value of the episode.
         * @param {Object} event - vue js modal event
         */
        beforeFailedSearchModalClose(event) {
            this.searchedEpisode = event.params.episode;
        },
        retryDownload(episode) {
            const { config } = this;
            return (config.failedDownloads.enabled && ['Snatched', 'Snatched (Proper)', 'Snatched (Best)', 'Downloaded'].includes(episode.status));
        },
        forcedSearch(episode, searchType) {
            const { show } = this;
            const episodeIdentifier = episode.slug;
            let data = {};
            
            if (episode) {
                data = {
                    showslug: show.id.slug,
                    episodes: [ episodeIdentifier ],
                    options: {}
                }
            }
            
            this.$refs[`search-${episodeIdentifier}`].src = `images/loading16-dark.gif`;
            api.post(`search/${searchType}`, data) // eslint-disable-line no-undef
                .then( _ => {
                    if (episode) {
                        console.info(`started search for show: ${show.id.slug} episode: ${episodeIdentifier}`);
                        this.$refs[`search-${episodeIdentifier}`].src = `images/queued.png`;
                        this.$refs[`search-${episodeIdentifier}`].disabled = true;
                    } else {
                        console.info(`started a full backlog search`);
                    }
                }).catch(error => {
                    console.error(String(error));
                    if (episode) {
                        this.$refs[`search-${episodeIdentifier}`].src = `images/no16.png`;
                    }
                });

        },
        /**
         * Start a backlog search or failed search for the specific episode.
         * A failed search is started depending on the current episodes status.
         * @param {Object} episode - Episode object. If no episode object is passed, a backlog search is started.
         */
        queueSearch(episode) {
            const { $modal, forcedSearch, retryDownload } = this;
            const episodeIdentifier = episode.slug;
            if (episode) {
                if (this.$refs[`search-${episodeIdentifier}`].disabled === true) {
                    return;
                }

                if (retryDownload(episode)) {
                    $modal.show('query-mark-failed-and-search', { episode });
                } else {
                    forcedSearch(episode, 'backlog');
                }
            }
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
                // If there is not a match on the xem table, display it as a medusa scene exception
                bindData = {
                    id: `xem-exception-season-${foundInXem ? xemSeasons[0] : season}`,
                    alt: foundInXem ? '[xem]' : '[medusa]',
                    src: foundInXem ? 'images/xem.png' : 'images/ico/favicon-16.png',
                    title: xemSeasons.reduce(function(a, b) {
                        return a.concat(allSceneExceptions[b]);
                    }, []).join(', '),
                }
            }

            return bindData;
        },
        toggleColumn(index) {
            // Set hidden to inverse of what it currently is
            this.$set( this.columns[ index ], 'hidden', ! this.columns[ index ].hidden );
        },
        getCookie(key) {
            const cookie = this.$cookie.get(key);
            return JSON.parse(cookie);
        },
        setCookie(key, value) {
            return this.$cookie.set(key, JSON.stringify(value));
        },
        updateEpisodeWatched(episode, watched) {
            const { id, indexer, getShow, show } = this;
            const patchData = {};

            patchData[episode.slug] = { watched };
            
            api.patch('series/' + show.id.slug + '/episodes', patchData) // eslint-disable-line no-undef
                .then( _ => {
                    console.info(`patched episode ${episode.slug} with watched set to ${watched}`);
                    getShow({ id, indexer, detailed: true });
                }).catch(error => {
                    console.error(String(error));
                });
        },
    },
    watch: {
        'show.id.slug': function(slug) { // eslint-disable-line object-shorthand
            // Show's slug has changed, meaning the show's page has finished loading.
            if (slug) {
                updateSearchIcons(slug, this);
            }
        },
        columns: {
            handler: function(newVal) { // eslint-disable-line object-shorthand
                // Monitor the columns, to update the cookies, when changed.
                const { setCookie } = this;
                for (const column of newVal) {
                    if (column) {
                        setCookie(`displayShow-hide-field-${column.label}`, column.hidden)
                    }
                }
            },
            deep: true
        },
        paginationPerPage(newVal) {
            const { setCookie } = this;
            setCookie('displayShow-pagination-perPage', newVal)
        }
    }
};
</script>

<style scope>
.vgt-global-search__input.vgt-pull-left {
    float: left;
    height: 40px;
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

.unaired {
    background-color: rgb(245, 241, 228);
}

.skipped {
    background-color: rgb(190, 222, 237);
}

.preferred {
    background-color: rgb(195, 227, 200);
}

.archived {
    background-color: rgb(195, 227, 200);
}

.allowed {
    background-color: rgb(255, 218, 138);
}

.wanted {
    background-color: rgb(255, 176, 176);
}

.snatched {
    background-color: rgb(235, 193, 234);
}

.downloaded {
    background-color: rgb(195, 227, 200);
}

.failed {
    background-color: rgb(255, 153, 153);
}

span.unaired {
    color: rgb(88, 75, 32);
}

span.skipped {
    color: rgb(29, 80, 104);
}

span.preffered {
    color: rgb(41, 87, 48);
}

span.allowed {
    color: rgb(118, 81, 0);
}

span.wanted {
    color: rgb(137, 0, 0);
}

span.snatched {
    color: rgb(101, 33, 100);
}

span.unaired b,
span.skipped b,
span.preferred b,
span.allowed b,
span.wanted b,
span.snatched b {
    color: rgb(0, 0, 0);
    font-weight: 800;
}

td.col-footer {
    text-align: left !important;
}

.vgt-wrap__footer {
    color: rgb(255, 255, 255);
    padding: 1em;
    background-color: rgb(51, 51, 51);
    margin-bottom: 1em;
    display: flex;
    justify-content: space-between;
}

.footer__row-count, .footer__navigation__page-info {
    display: inline;
}

.footer__row-count__label {
    margin-right: 1em;
}

.vgt-wrap__footer .footer__navigation {
    font-size: 14px;
}

.vgt-pull-right {
    float: right!important;
}

.vgt-wrap__footer .footer__navigation__page-btn .chevron {
    width: 24px;
    height: 24px;
    border-radius: 15%;
    position: relative;
    margin: 0 8px;
}

.vgt-wrap__footer .footer__navigation__info, .vgt-wrap__footer .footer__navigation__page-info {
    display: inline-flex;
    color: #909399;
    margin: 0 16px;
    margin-top: 0px;
    margin-right: 16px;
    margin-bottom: 0px;
    margin-left: 16px;
}

.select-info span {
    margin-left: 5px;
    line-height: 40px;
}


/** Style the modal. This should be saved somewhere, where we create one modal template with slots, and style that.*/
.modal-container {
    border: 1px solid rgb(17, 17, 17);
    box-shadow: 0 0 12px 0 rgba(0, 0, 0, 0.175);
    border-radius: 0;
}

.modal-header {
    padding: 9px 15px;
    border-bottom: none;
    border-radius: 0;
    background-color: rgb(55, 55, 55);
}

.modal-content {
    background: rgb(34, 34, 34);
    border-radius: 0;
    border: 1px solid rgba(0,0,0,.2);
    box-shadow: 0 5px 15px rgba(0,0,0,.5);
}

.modal-body {
    background: rgb(34, 34, 34);
    overflow-y: auto;
}

.modal-footer {
    border-top: none;
    text-align: center;
}

</style>
