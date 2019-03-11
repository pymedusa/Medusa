<template>
    <div class="display-show-template">
        <input type="hidden" id="series-id" value="" />
        <input type="hidden" id="indexer-name" value="" />
        <input type="hidden" id="series-slug" value="" />

        <show-header @reflow="reflowLayout" type="show"
            :show-id="id" :show-indexer="indexer"
        ></show-header>
        
        <div class="row">
            <div class="col-md-12 top-15">
                <vue-good-table v-if="show.seasons"
                :columns="columns"
                :rows="show.seasons.slice().reverse()"
                :groupOptions="{ enabled: true }"
                :sort-options="{
                    enabled: true,
                    initialSortBy: {field: 'episode', type: 'desc'}
                }">
                <div slot="table-actions">
                    <div class="button-group pull-right">
                        <button type="button" class="btn btn-default btn-sm dropdown-toggle" data-toggle="dropdown"><span class="fa fa-cog" aria-hidden="false">Select Columns</span> <span class="caret"></span></button>
                        <ul class="dropdown-menu" style="top: auto; left: auto;">
                            <li v-for="(column, index) in columns" :key="index">
                                <a href="#" class="small" tabIndex="-1" @click.prevent="toggleColumn( index, $event )"><input :checked="!column.hidden" type="checkbox"/>&nbsp;{{column.label}}</a>
                            </li>
                        </ul>
                    </div>
                </div>

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
                        <app-link v-if="props.row.season !== 0" :class="retryDownload(props.row) ? 'epRetry' : 'epSearch'" :id="show.indexer + 'x' + show.id[show.indexer] + 'x' + props.row.season + 'x' + props.row.episode" :name="show.indexer + 'x' + show.id[show.indexer] + 'x' + props.row.season + 'x' + props.row.episode" :href="'home/' + (retryDownload(props.row) ? 'retryEpisode' : 'searchEpisode') + '?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&season=' + props.row.season + '&episode=' + props.row.episode"><img data-ep-search src="images/search16.png" height="16" alt="retryDownload(props.row) ? 'retry' : 'search'" title="retryDownload(props.row) ? 'Retry Download' : 'Forced Seach'"/></app-link>
                        <app-link class="epManualSearch" :id="show.indexer + 'x' + show.id[show.indexer] + 'x' + props.row.season + 'x' + props.row.episode" :name="show.indexer + 'x' + show.id[show.indexer] + 'x' + props.row.season + 'x' + props.row.episode" :href="'home/snatchSelection?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&season=' + props.row.season + '&episode=' + props.row.episode"><img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search" /></app-link>
                        <app-link v-if="showSubtitleButton(props.row)" class="epSubtitlesSearch" :href="'home/searchEpisodeSubtitles?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer] + '&season=' + props.row.season + '&episode=' + props.row.episode"><img src="images/closed_captioning.png" height="16" alt="search subtitles" title="Search Subtitles" /></app-link>
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
        <div id="askmanualSubtitleSearchModal" class="modal fade">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                        <h4 class="modal-title">Subtitle search</h4>
                    </div>
                    <div class="modal-body">
                        <p>Do you want to manually pick subtitles or let us choose it for you?</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn-medusa btn-info" data-dismiss="modal">Auto</button>
                        <button type="button" class="btn-medusa btn-success" data-dismiss="modal">Manual</button>
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
import { VueGoodTable  } from 'vue-good-table';
import EpisodeTable from './episode-table.vue';
import ShowHeader from './show-header.vue';

export default {
    name: 'show',
    components: {
        AppLink,
        VueGoodTable,
        EpisodeTable,
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
            search: '',
            columns: [{
                label: 'nfo',
                field: 'content.hasNfo',
                type: 'boolean'
            },{
                label: 'tbn',
                field: 'content.hasTbn',
                type: 'boolean'
            },{
                label: 'Episode',
                field: 'episode',
                type: 'number'
            }, {
                label: 'Absolute Number',
                field: 'absoluteNumber',
                type: 'number'
            }, {
                label: 'Scene',
                field: 'scene',
                type: 'number'
            }, {
                label: 'Scene Absolute',
                field: 'sceneAbsolute',
                type: 'number'
            }, {
                label: 'Title',
                field: 'title'
            }, {
                label: 'File',
                field: 'file.location'
            }, {
                label: 'Size',
                field: 'file.size',
                type: 'number'
            }, {
                // For now i'm using a custom function the parse it. As the type: date, isn't working for us.
                label: 'Air date',
                field: this.parseDateFn
                // type: 'date',
                // dateInputFormat: 'YYYY-MM-DD HH:mm:ssZ ', // expects 2018-03-16
                // dateOutputFormat: 'MMM Do YYYY', // outputs Mar 16th 2018
            }, {
                label: 'Download',
                field: 'download'
            }, {
                label: 'Subtitles',
                field: 'subtitles',
                sortable: false
            }, {
                label: 'Status',
                field: 'status'
            }, {
                label: 'Search',
                field: 'search'
            }]
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
                debugger;
                const reg = /collapseSeason-(\d+)/g;
                const result = reg.exec(this.id);
                $('#showseason-' + result[1]).text('Show Episodes');
                $('#season-' + result[1] + '-cols').addClass('shadow');
            });
            element.addEventListener('show.bs.collapse', () => {
                // On show
                debugger;
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
        parseDateFn(row) {
            return formatDate(parse(row.airDate), 'DD/MM/YYYY, hh:mm a');
        },
        parseSubtitlesFn(row) {
            debugger;
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

<style>
.table {
    width: 100%;
    max-width: 100%;
    margin-bottom: 20px;
}

div.season-table > div.table-responsive > table > thead {
    display: none;
}
.table-striped>tbody>tr:nth-of-type(odd) {
    background-color: transparent;
}
.VueTables__child-row-toggler {
    width: 16px;
    height: 16px;
    line-height: 16px;
    display: block;
    margin: auto;
    text-align: center;
}
 
.VueTables__child-row-toggler--closed::before {
    content: "+";
}
 
.VueTables__child-row-toggler--open::before {
    content: "-";
}
.VueTables__table > .float-right {
    float: right;
}
.VueTables.episodes {
    display: inline-block;
}
.table-bordered, .table-bordered>tbody>tr>td, 
.table-bordered>tbody>tr>th, .table-bordered>tfoot>tr>td, 
.table-bordered>tfoot>tr>th, 
.table-bordered>thead>tr>td, .table-bordered>thead>tr>th {
    border: none;
}
.table>tbody>tr>td, .table>tbody>tr>th, .table>tfoot>tr>td, 
.table>tfoot>tr>th, .table>thead>tr>td, .table>thead>tr>th {
    border-top: none;
}
.table-hover>tbody>tr:hover, .table>tbody>tr.active>td, .table>tbody>tr.active>th, .table>tbody>tr>td.active, .table>tbody>tr>th.active, .table>tfoot>tr.active>td, .table>tfoot>tr.active>th, .table>tfoot>tr>td.active, .table>tfoot>tr>th.active, .table>thead>tr.active>td, .table>thead>tr.active>th, .table>thead>tr>td.active, .table>thead>tr>th.active {
    background-color: transparent;
}

div.season-table > table.VueTables__table.table {
    width: 250px;
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
