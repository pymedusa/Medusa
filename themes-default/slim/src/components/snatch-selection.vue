<template>
    <div id="snatch-selection-template" class="snatch-selection-template">
        <vue-snotify />
        <backstretch v-if="show.id.slug" :slug="show.id.slug" />

        <show-header type="snatch-selection"
                     ref="show-header"
                     :show-id="id"
                     :show-indexer="indexer"
                     :manual-search-type="'episode'"
                     @update-overview-status="filterByOverviewStatus = $event"
        />

        <show-history v-show="show && season" v-bind="{ show, season, episode }" :key="`history-${show.id.slug}-${season}-${episode || ''}`" />

        <show-results v-show="show && season" class="table-layout" v-bind="{ show, season, episode }" :key="`results-${show.id.slug}-${season}-${episode || ''}`" />

    </div>
</template>

<script>
import { mapState, mapGetters, mapActions } from 'vuex';
import { AppLink } from './helpers';
import ShowHeader from './show-header.vue';
import ShowHistory from './show-history.vue';
import ShowResults from './show-results.vue';
import Backstretch from './backstretch.vue';

export default {
    name: 'snatch-selection',
    template: '#snatch-selection-template',
    components: {
        Backstretch,
        ShowHeader,
        ShowHistory,
        ShowResults
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
    computed: {
        ...mapState({
            shows: state => state.shows.shows,
            config: state => state.config,
            search: state => state.config.search,
            history: state => state.history
        }),
        ...mapGetters({
            show: 'getCurrentShow',
            effectiveIgnored: 'effectiveIgnored',
            effectiveRequired: 'effectiveRequired',
            getShowHistoryBySlug: 'getShowHistoryBySlug',
            getEpisode: 'getEpisode'
        }),
        indexer() {
            return this.$route.query.indexername;
        },
        id() {
            return Number(this.$route.query.seriesid);
        },
        season() {
            return Number(this.$route.query.season);
        },
        episode() {
            return Number(this.$route.query.episode);
        }
    },
    methods: {
        ...mapActions({
            getShow: 'getShow', // Map `this.getShow()` to `this.$store.dispatch('getShow')`
            getHistory: 'getHistory'
        }),
        // /**
        //  * Attaches IMDB tooltip,
        //  */
        // reflowLayout() {
        //     attachImdbTooltip(); // eslint-disable-line no-undef
        // },
        getReleaseNameClasses(name) {
            const { effectiveIgnored, effectiveRequired, search, show } = this;
            const classes = [];

            if (effectiveIgnored(show).map(word => {
                return name.toLowerCase().includes(word.toLowerCase());
            }).filter(x => x === true).length > 0) {
                classes.push('global-ignored');
            }

            if (effectiveRequired(show).map(word => {
                return name.toLowerCase().includes(word.toLowerCase());
            }).filter(x => x === true).length > 0) {
                classes.push('global-required');
            }

            if (search.filters.undesired.map(word => {
                return name.toLowerCase().includes(word.toLowerCase());
            }).filter(x => x === true).length > 0) {
                classes.push('global-undesired');
            }

            /** Disabled for now. Because global + series ignored can be concatenated or excluded. So it's not that simple to color them. */
            // if (this.show.config.release.ignoredWords.map( word => {
            //     return name.toLowerCase().includes(word.toLowerCase());
            // }).filter(x => x === true).length) {
            //     classes.push('show-ignored');
            // }

            // if (this.show.config.release.requiredWords.map( word => {
            //     return name.toLowerCase().includes(word.toLowerCase());
            // }).filter(x => x === true).length) {
            //     classes.push('show-required');
            // }

            return classes.join(' ');
        }
    },
    mounted() {
        const {
            indexer,
            id,
            show,
            getShow,
            $store
        } = this;

        // Let's tell the store which show we currently want as current.
        $store.commit('currentShow', {
            indexer,
            id
        });

        // getHistory();

        // We need the show info, so let's get it.
        if (!show || !show.id.slug) {
            getShow({ id, indexer, detailed: false });
        }

        // this.$watch('show', () => {
        //     this.$nextTick(() => this.reflowLayout());
        // });

        // ['load', 'resize'].map(event => {
        //     return window.addEventListener(event, () => {
        //         this.reflowLayout();
        //     });
        // });

        const updateSpinner = function(message, showSpinner) {
            // Get spinner object as needed
            const spinner = $('#searchNotification');
            if (showSpinner) {
                message = '<img id="searchingAnim" src="images/loading32' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />&nbsp;' + message;
            }
            $(spinner).empty().append(message);
        };

        // // Check the previous status of the history table, for hidden or shown, through the data attribute
        // // data-history-toggle-hidden
        // function toggleHistoryTable() { // eslint-disable-line no-unused-vars
        //     // Get previous state which was saved on the wrapper
        //     const showOrHide = $('#wrapper').attr('data-history-toggle');
        //     $('#historydata').collapse(showOrHide);
        // }

        // $.fn.loadContainer = function(path, loadingTxt, errorTxt, callback) {
        //     updateSpinner(loadingTxt);
        //     $('#manualSearchMeta').load(path + ' #manualSearchMeta meta');
        //     $(this).load(path + ' #manualSearchTbody tr', (response, status) => {
        //         if (status === 'error') {
        //             updateSpinner(errorTxt, false);
        //         }
        //         if (typeof callback !== 'undefined') {
        //             callback();
        //         }
        //     });
        // };

        // // Click event for the download button for snatching a result
        // $(document.body).on('click', '.epManualSearch', event => {
        //     event.preventDefault();
        //     const link = event.currentTarget;
        //     $(link).children('img').prop('src', 'images/loading16.gif');
        //     $.getJSON(event.currentTarget.href, data => {
        //         if (data.result === 'success') {
        //             $(link).children('img').prop('src', 'images/save.png');
        //         } else {
        //             $(link).children('img').prop('src', 'images/no16.png');
        //         }
        //     });
        // });

        // function initTableSorter(table) {
        //     // Nasty hack to re-initialize tablesorter after refresh
        //     $(table).tablesorter({
        //         widgets: ['saveSort', 'stickyHeaders', 'columnSelector', 'filter'],
        //         widgetOptions: {
        //             filter_columnFilters: true, // eslint-disable-line camelcase
        //             filter_hideFilters: true, // eslint-disable-line camelcase
        //             filter_saveFilters: true, // eslint-disable-line camelcase
        //             columnSelector_saveColumns: true, // eslint-disable-line camelcase
        //             columnSelector_layout: '<label><input type="checkbox">{name}</label>', // eslint-disable-line camelcase
        //             columnSelector_mediaquery: false, // eslint-disable-line camelcase
        //             columnSelector_cssChecked: 'checked' // eslint-disable-line camelcase
        //         },
        //         textExtraction: (function() {
        //             return {
        //                 // 2: Provider
        //                 2(node) {
        //                     return $(node).find('img').attr('title');
        //                 },
        //                 // 6: The size column needs an explicit field for the filtering on raw size.
        //                 6(node) {
        //                     return node.getAttribute('data-size');
        //                 },
        //                 // 9: Published date
        //                 9(node) {
        //                     return node.getAttribute('data-datetime');
        //                 },
        //                 // 10: Added date
        //                 10(node) {
        //                     return node.getAttribute('data-datetime');
        //                 }
        //             };
        //         })(),
        //         headers: {
        //             9: { sorter: 'realISODate' }, // Published
        //             10: { sorter: 'realISODate' }, // Added
        //             11: { sorter: false, parser: false } // Snatch link
        //         }
        //     });
        // }

        // function checkCacheUpdates(repeat) {
        //     let pollInterval = 5000;
        //     repeat = repeat || true;

        //     const indexerName = $('meta[data-last-prov-updates]').attr('data-indexer-name');
        //     const seriesId = $('meta[data-last-prov-updates]').attr('data-series-id');
        //     const season = $('meta[data-last-prov-updates]').attr('data-season');
        //     const episode = $('meta[data-last-prov-updates]').attr('data-episode');
        //     const data = $('meta[data-last-prov-updates]').data('last-prov-updates');
        //     const manualSearchType = $('meta[data-last-prov-updates]').attr('data-manual-search-type');

        //     const checkParams = [indexerName, seriesId, season, episode].every(checkIsTrue => {
        //         return checkIsTrue;
        //     });

        //     if (!checkParams) {
        //         console.log(
        //             'Something went wrong in getting the paramaters from dom.' +
        //             ` indexerName: ${indexerName}, seriesId: ${seriesId}, season: ${season}, episode: ${episode}`
        //         );
        //         return;
        //     }

        //     let urlParams = '?indexername=' + indexerName + '&seriesid=' + seriesId + '&season=' + season + '&episode=' + episode;

        //     if (manualSearchType === 'season') {
        //         urlParams += '&manual_search_type=' + manualSearchType;
        //     }

        //     if (!$.isNumeric(seriesId) || !$.isNumeric(season) || !$.isNumeric(episode)) {
        //         setTimeout(() => {
        //             checkCacheUpdates(true);
        //         }, 200);
        //     }

        //     $.ajax({
        //         url: 'home/manualSearchCheckCache' + urlParams,
        //         type: 'GET',
        //         data,
        //         contentType: 'application/json',
        //         error() {
        //             // Repeat = false;
        //             console.log('Error occurred!!');
        //             $('.manualSearchButton').removeAttr('disabled');
        //         },
        //         complete() {
        //             if (repeat) {
        //                 setTimeout(checkCacheUpdates, pollInterval);
        //             }
        //         },
        //         timeout: 15000 // Timeout after 15s
        //     }).done(data => {
        //         // @TODO: Combine the lower if statements
        //         if (data === '') {
        //             updateSpinner('Search finished', false);
        //             $('.manualSearchButton').removeAttr('disabled');
        //             repeat = false;
        //         }

        //         if (data.result === 'refresh') {
        //             window.location.reload();
        //             updateSpinner('Refreshed results...', true);
        //         }
        //         if (data.result === 'searching') {
        //             // Ep is searched, you will get a results any minute now
        //             pollInterval = 5000;
        //             $('.manualSearchButton').prop('disabled', true);
        //             updateSpinner('The episode is being searched, please wait......', true);
        //         }
        //         if (data.result === 'queued') {
        //             // Ep is queued, this might take some time to get results
        //             pollInterval = 7000;
        //             $('.manualSearchButton').prop('disabled', true);
        //             updateSpinner('The episode has been queued, because another search is taking place. please wait..', true);
        //         }
        //         if (data.result === 'finished') {
        //             // Ep search is finished
        //             updateSpinner('Search finished', false);
        //             $('.manualSearchButton').removeAttr('disabled');
        //             repeat = false;
        //             $('#srchresults').trigger('update', true);
        //             $('[datetime]').timeago();
        //         }
        //         if (data.result === 'error') {
        //             // Ep search is finished but with an error
        //             console.log('Probably tried to call manualSelectCheckCache, while page was being refreshed.');
        //             $('.manualSearchButton').removeAttr('disabled');
        //             repeat = true;
        //         }
        //     });
        // }

        // setTimeout(checkCacheUpdates, 2000);

        // // Click event for the reload results and force search buttons
        // $(document.body).on('click', '.manualSearchButton', event => {
        //     event.preventDefault();
        //     $('.manualSearchButton').prop('disabled', true);
        //     const indexerName = $('meta[data-last-prov-updates]').attr('data-indexer-name');
        //     const seriesId = $('meta[data-last-prov-updates]').attr('data-series-id');
        //     const season = $('meta[data-last-prov-updates]').attr('data-season');
        //     const episode = $('meta[data-last-prov-updates]').attr('data-episode');
        //     const manualSearchType = $('meta[data-last-prov-updates]').attr('data-manual-search-type');
        //     const forceSearch = $(event.currentTarget).attr('data-force-search');

        //     const checkParams = [indexerName, seriesId, season, episode].every(checkIsTrue => {
        //         return checkIsTrue;
        //     });

        //     if (!checkParams) {
        //         console.log(
        //             'Something went wrong in getting the paramaters from dom.' +
        //             ` indexerName: ${indexerName}, seriesId: ${seriesId}, season: ${season}, episode: ${episode}`
        //         );
        //         return;
        //     }

        //     if ($.isNumeric(seriesId) && $.isNumeric(season) && $.isNumeric(episode)) {
        //         updateSpinner('Started a forced manual search...', true);
        //         $.getJSON('home/snatchSelection', {
        //             indexername: indexerName,
        //             seriesid: seriesId,
        //             season,
        //             episode,
        //             manual_search_type: manualSearchType, // eslint-disable-line camelcase
        //             perform_search: forceSearch // eslint-disable-line camelcase
        //         });
        //         // Force the search, but give the checkCacheUpdates the time to start up a search thread
        //         setTimeout(() => {
        //             checkCacheUpdates(true);
        //         }, 2000);
        //     }
        // });

        // Moved and rewritten this from displayShow. This changes the button when clicked for collapsing/expanding the
        // "Show History" button to show or hide the snatch/download/failed history for a manual searched episode or pack.

        // $('#popover').popover({
        //     placement: 'bottom',
        //     html: true, // Required if content has HTML
        //     content: '<div id="popover-target"></div>'
        // }).on('shown.bs.popover', () => { // Bootstrap popover event triggered when the popover opens
        //     $.tablesorter.columnSelector.attachTo($('#srchresults'), '#popover-target');
        // });

        // $('#btnReset').click(() => {
        //     $('#showTable')
        //         .trigger('saveSortReset') // Clear saved sort
        //         .trigger('sortReset'); // Reset current table sort
        //     return false;
        // });

        // initTableSorter('#srchresults');
        // this.reflowLayout();

        // $('body').on('hide.bs.collapse', '.collapse.toggle', () => {
        //     $('#showhistory').text('Show History');
        //     $('#wrapper').prop('data-history-toggle', 'hide');
        // });
        // $('body').on('show.bs.collapse', '.collapse.toggle', () => {
        //     $('#showhistory').text('Hide History');
        //     $('#wrapper').prop('data-history-toggle', 'show');
        // });

        // $(document.body).on('click', '.release-name-ellipses, .release-name-ellipses-toggled', event => {
        //     const target = $(event.currentTarget);

        //     if (target.hasClass('release-name-ellipses')) {
        //         target.switchClass('release-name-ellipses', 'release-name-ellipses-toggled', 100);
        //     } else {
        //         target.switchClass('release-name-ellipses-toggled', 'release-name-ellipses', 100);
        //     }
        // });
    }
};
</script>

<style scoped>
span.global-ignored {
    color: red;
}

span.show-ignored {
    color: red;
    font-style: italic;
}

span.global-required {
    color: green;
}

span.show-required {
    color: green;
    font-style: italic;
}

span.global-undesired {
    color: orange;
}

/** Use this as table styling for all table layouts */
.snatch-selection-template >>> .vgt-table {
    width: 100%;
    margin-right: auto;
    margin-left: auto;
    text-align: left;
    border-spacing: 0;
}

.snatch-selection-template >>> .vgt-table th,
.snatch-selection-template >>> .vgt-table td {
    padding: 4px;
    vertical-align: middle;
}

/* remove extra border from left edge */
.snatch-selection-template >>> .vgt-table th:first-child,
.snatch-selection-template >>> .vgt-table td:first-child {
    border-left: none;
}

.snatch-selection-template >>> .vgt-table th {
    text-align: center;
    border-collapse: collapse;
    font-weight: normal;
}

.snatch-selection-template >>> .vgt-table span.break-word {
    word-wrap: break-word;
}

.snatch-selection-template >>> .vgt-table thead th.sorting.sorting-asc {
    background-position-x: right;
    background-position-y: bottom;
}

.snatch-selection-template >>> .vgt-table thead th.sorting {
    background-repeat: no-repeat;
}

.snatch-selection-template >>> .vgt-table thead th {
    padding: 4px;
    cursor: default;
}

.snatch-selection-template >>> .vgt-table input.tablesorter-filter {
    width: 98%;
    height: auto;
    -webkit-box-sizing: border-box;
    -moz-box-sizing: border-box;
    box-sizing: border-box;
}

.snatch-selection-template >>> .vgt-table tr.tablesorter-filter-row,
.snatch-selection-template >>> .vgt-table tr.tablesorter-filter-row td {
    text-align: center;
}

/* optional disabled input styling */
.snatch-selection-template >>> .vgt-table input.tablesorter-filter-row .disabled {
    display: none;
}

.tablesorter-header-inner {
    padding: 0 2px;
    text-align: center;
}

.snatch-selection-template >>> .vgt-table tfoot tr {
    text-align: center;
    border-collapse: collapse;
}

.snatch-selection-template >>> .vgt-table tfoot a {
    text-decoration: none;
}

.snatch-selection-template >>> .vgt-table th.vgt-row-header {
    text-align: left;
}

.snatch-selection-template >>> .vgt-table .season-header {
    display: inline;
    margin-left: 5px;
}

.snatch-selection-template >>> .vgt-table tr.spacer {
    height: 25px;
}

.snatch-selection-template >>> .vgt-dropdown-menu {
    position: absolute;
    z-index: 1000;
    float: left;
    min-width: 160px;
    padding: 5px 0;
    margin: 2px 0 0;
    font-size: 14px;
    text-align: left;
    list-style: none;
    background-clip: padding-box;
    border-radius: 4px;
}

.snatch-selection-template >>> .vgt-dropdown-menu > li > span {
    display: block;
    padding: 3px 20px;
    clear: both;
    font-weight: 400;
    line-height: 1.42857143;
    white-space: nowrap;
}

.snatch-selection-template >>> .align-center {
    display: flex;
    justify-content: center;
}

.snatch-selection-template >>> .indexer-image :not(:last-child) {
    margin-right: 5px;
}

.snatch-selection-template >>> .button-row {
    width: 100%;
    display: inline-block;
}

show-history {
    margin-bottom: 10px;
}
</style>
