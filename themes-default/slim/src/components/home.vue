<template>
    <div id="home">
        <input type="hidden" id="background-series-slug" value="" />

        <div class="row" v-if="layout === 'poster'">
            <div class="col-lg-9 col-md-12 col-sm-12 col-xs-12 pull-right">
                <div class="pull-right">
                    <div class="show-option pull-right">
                        <input id="filterShowName" class="form-control form-control-inline input-sm input200" type="search" placeholder="Filter Show Name">
                    </div>
                    <div class="show-option pull-right"> Direction:
                        <!-- These need to patch apiv2 on change! -->
                        <select v-model="stateLayout.posterSortdir" id="postersortdirection" class="form-control form-control-inline input-sm">
                            <option :value="1">Ascending</option>
                            <option :value="0">Descending</option>
                        </select>
                    </div>

                    <div class="show-option pull-right"> Sort By:
                    <select v-model="stateLayout.posterSortby" id="postersort" class="form-control form-control-inline input-sm">
                        <option v-for="option in posterSortByOptions" :value="option.value" :key="option.value" @change="changePosterSortBy">
                            {{ option.text }}
                        </option>
                        <!-- <option value="name" data-sort="setPosterSortBy/?sort=name">Name</option>
                        <option value="date" data-sort="setPosterSortBy/?sort=date">Next Episode</option>
                        <option value="network" data-sort="setPosterSortBy/?sort=network">Network</option>
                        <option value="progress" data-sort="setPosterSortBy/?sort=progress">Progress</option>
                        <option value="indexer" data-sort="setPosterSortBy/?sort=indexer">Indexer</option> -->
                    </select>
                    </div>
                    <div class="show-option pull-right">
                        Poster Size:
                        <div style="width: 100px; display: inline-block; margin-left: 7px;" id="posterSizeSlider"></div>
                    </div>
                </div>
            </div>
        </div> <!-- row !-->

        <div class="row">
            <div class="col-md-12">
                <div class="pull-left" id="showRoot" style="display: none;">
                    <select name="showRootDir" id="showRootDir" class="form-control form-control-inline input-sm"></select>
                </div>
                <div class="show-option pull-right">
                    <template v-if="layout !== 'poster'">
                        <span class="show-option">
                            <button id="popover" type="button" class="btn-medusa btn-inline">
                                Select Columns <b class="caret"></b>
                            </button>
                        </span> <span class="show-option">
                            <button type="button" class="resetsorting btn-medusa btn-inline">Clear
                                Filter(s)</button>
                        </span>&nbsp;
                    </template>
                    Layout: <select v-model="layout" name="layout" class="form-control form-control-inline input-sm show-layout">
                        <option value="poster">Poster</option>
                        <option value="small">Small Poster</option>
                        <option value="banner">Banner</option>
                        <option value="simple">Simple</option>
                    </select>
                </div>
            </div>
        </div><!-- end row -->

        <div class="row">
            <div class="col-md-12">
                <!-- Split in tabs -->
                <div id="showTabs" v-if="config.animeSplitHome && config.animeSplitHomeInTabs">
                    <!-- Nav tabs -->
                    <ul>
                        <li v-for="showList in showLists" :key="showList.listTitle">
                            <app-link :href="`#${listTitle}TabContent`" :id="`${listTitle}Tab`">{{ listTitle }}</app-link>
                        </li>
                    </ul>
                    <!-- Tab panes -->
                    <div id="showTabPanes">
                        <template v-if="['banner', 'simple', 'small', 'poster'].includes(layout)">
                            <div v-for="showList in showLists" :key="showList.listTitle" :id="`${showList.listTitle}TabContent`">
                                <show-list v-bind="{ listTitle, layout, shows, header: true }"></show-list>
                            </div> <!-- #...TabContent -->
                        </template>
                    </div><!-- #showTabPanes -->
                </div> <!-- #showTabs -->
                <template v-else>
                    <!-- if not app.HOME_LAYOUT in ['banner', 'simple']:
                        <include file="/partials/home/{app.HOME_LAYOUT}.mako"/>
                     endif -->
                    <template v-if="['banner', 'simple', 'small', 'poster'].includes(layout)">
                        <show-list v-for="showList in showLists" :key="showList.listTitle" v-bind="{ listTitle: showList.listTitle, layout, shows: showList.shows, header: showLists.length > 1 }"/>
                    </template>
                </template>
            </div>
        </div>
    </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from 'vuex';
import debounce from 'lodash/debounce';
import { api } from '../api';
import { AppLink } from './helpers';
import ShowList from './show-list';
import LazyLoad from 'vanilla-lazyload';

export default {
    name: 'home',
    components: {
        AppLink,
        ShowList
    },
    data() {
        return {
            layoutOptions: [
                { value: 'poster', text: 'Poster' },
                { value: 'small', text: 'Small Poster' },
                { value: 'banner', text: 'Banner' },
                { value: 'simple', text: 'Simple' }
            ],
            postSortDirOptions: [
                { value: '0', text: 'Descending' },
                { value: '1', text: 'Ascending' }
            ],
            posterSortByOptions: [
                { text: 'Name', value: 'name' },
                { text: 'Next episode', value: 'date' },
                { text: 'Network', value: 'network' },
                { text: 'Progress', value: 'progress' },
                { text: 'Indexer', value: 'indexer' }
            ],
        };
    },
    computed: {
        ...mapState({
            config: state => state.config,
            // We don't directly need this. But at some point we need to translate indexerName to id, which uses the state.indexers module.
            indexers: state => state.indexers,
            // Renamed because of the computed property 'layout'.
            stateLayout: state => state.layout,
            stats: state => state.stats
        }),
        ...mapGetters({
            showsWithStats: 'showsWithStats'
        }),
        layout: {
            get() {
                const { stateLayout } = this;
                return stateLayout.home;
            },
            set(layout) {
                const { setLayout } = this;
                const page = 'home';
                setLayout({ page, layout });
            }
        },
        showLists() {
            const { indexers, stateLayout, showsWithStats, stats } = this;
            if (stats.show.stats.length === 0 || !indexers.indexers) {
                return;
            }

            const shows = showsWithStats;
            return stateLayout.show.showListOrder.map(listTitle => {
                return (
                    { listTitle, shows: shows.filter(show => show.config.anime === (listTitle === 'Anime')) }
                );
            });
        },
        imgLazyLoad() {
            console.log('imgLazyLoad object constructud!');
            return new LazyLoad({
                // Example of options object -> see options section
                threshold: 500
            });
        }
    },
    methods: {
        ...mapActions({
            setLayout: 'setLayout',
            setConfig: 'setConfig',
            getShows: 'getShows',
            getStats: 'getStats'
        }),
        initializePosterSizeSlider() {
            const resizePosters = newSize => {
                let fontSize;
                let logoWidth;
                let borderRadius;
                let borderWidth;
                if (newSize < 125) { // Small
                    borderRadius = 3;
                    borderWidth = 4;
                } else if (newSize < 175) { // Medium
                    fontSize = 9;
                    logoWidth = 40;
                    borderRadius = 4;
                    borderWidth = 5;
                } else { // Large
                    fontSize = 11;
                    logoWidth = 50;
                    borderRadius = 6;
                    borderWidth = 6;
                }

                // If there's a poster popup, remove it before resizing
                $('#posterPopup').remove();

                if (fontSize === undefined) {
                    $('.show-details').hide();
                } else {
                    $('.show-details').show();
                    $('.show-dlstats, .show-quality').css('fontSize', fontSize);
                    $('.show-network-image').css('width', logoWidth);
                }

                $('.show-container').css({
                    width: newSize,
                    borderWidth,
                    borderRadius
                });
            };

            let posterSize;
            if (typeof (Storage) !== 'undefined') {
                posterSize = parseInt(localStorage.getItem('posterSize'), 10);
            }
            if (typeof (posterSize) !== 'number' || isNaN(posterSize)) {
                posterSize = 188;
            }
            resizePosters(posterSize);

            $('#posterSizeSlider').slider({
                min: 75,
                max: 250,
                value: posterSize,
                change(e, ui) {
                    if (typeof (Storage) !== 'undefined') {
                        localStorage.setItem('posterSize', ui.value);
                    }
                    resizePosters(ui.value);
                    $('.show-grid').isotope('layout');
                }
            });
        },
        changePosterSortBy() {
            // Patch new posterSOrtBy value
            const { setConfig } = this;
        }
    },
    beforeMount() {
        // Wait for the next tick, so the component is rendered
        this.$nextTick(() => {
            $('#showTabs').tabs();
        });
    },
    mounted() {
        const { $snotify, config, stateLayout, setConfig, getShows, getStats } = this;

        getShows();
        getStats('show');

        // // Resets the tables sorting, needed as we only use a single call for both tables in tablesorter
        // $(document.body).on('click', '.resetsorting', () => {
        //     $('table').trigger('filterReset');
        // });

        // // Handle filtering in the poster layout
        // $(document.body).on('input', '#filterShowName', debounce(() => {
        //     $('.show-grid').isotope({
        //         filter() {
        //             const name = $(this).attr('data-name').toLowerCase();
        //             return name.includes($('#filterShowName').val().toLowerCase());
        //         }
        //     });
        // }, 500));

        // $(document.body).on('change', '#postersort', function() {
        //     $('.show-grid').isotope({ sortBy: $(this).val() });
        //     $.get($(this).find('option[value=' + $(this).val() + ']').attr('data-sort'));
        // });

        // $(document.body).on('change', '#postersortdirection', function() {
        //     $('.show-grid').isotope({ sortAscending: ($(this).val() === '1') });
        //     $.get($(this).find('option[value=' + $(this).val() + ']').attr('data-sort'));
        // });

        // $(document.body).on('change', '#showRootDir', function() {
        //     api.patch('config/main', {
        //         selectedRootIndex: parseInt($(this).val(), 10)
        //     }).then(response => {
        //         console.info(response);
        //         window.location.reload();
        //     }).catch(error => {
        //         console.info(error);
        //     });
        // });

        // const initializePage = () => {
            // Reset the layout for the activated tab (when using ui tabs)
            // $('#showTabs').tabs({
            //     activate() {
            //         $('.show-grid').isotope('layout');
            //     }
            // });

            // This needs to be refined to work a little faster.
            // $('.progressbar').each(function() {
            //     const percentage = $(this).data('progress-percentage');
            //     const classToAdd = percentage === 100 ? 100 : percentage > 80 ? 80 : percentage > 60 ? 60 : percentage > 40 ? 40 : 20; // eslint-disable-line no-nested-ternary
            //     $(this).progressbar({
            //         value: percentage
            //     });
            //     if ($(this).data('progress-text')) {
            //         $(this).append('<div class="progressbarText" title="' + $(this).data('progress-tip') + '">' + $(this).data('progress-text') + '</div>');
            //     }
            //     $(this).find('.ui-progressbar-value').addClass('progress-' + classToAdd);
            // });

            // $('img#network').on('error', function() {
            //     $(this).parent().text($(this).attr('alt'));
            //     $(this).remove();
            // });

            // $('#showListTableSeries:has(tbody tr), #showListTableAnime:has(tbody tr)').tablesorter({
            //     debug: false,
            //     sortList: [[7, 1], [2, 0]],
            //     textExtraction: (function() {
            //         return {
            //             0(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
            //             1(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
            //             3(node) { return $(node).find('span').prop('title').toLowerCase(); }, // eslint-disable-line brace-style
            //             4(node) { return $(node).find('a[data-indexer-name]').attr('data-indexer-name'); }, // eslint-disable-line brace-style
            //             5(node) { return $(node).find('span').text().toLowerCase(); }, // eslint-disable-line brace-style
            //             6(node) { return $(node).find('span:first').text(); }, // eslint-disable-line brace-style
            //             7(node) { return $(node).data('show-size'); }, // eslint-disable-line brace-style
            //             8(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
            //             10(node) { return $(node).find('img').attr('alt'); } // eslint-disable-line brace-style
            //         };
            //     })(),
            //     widgets: ['saveSort', 'zebra', 'stickyHeaders', 'filter', 'columnSelector'],
            //     headers: {
            //         0: { sorter: 'realISODate' },
            //         1: { sorter: 'realISODate' },
            //         2: { sorter: 'showNames' },
            //         4: { sorter: 'text' },
            //         5: { sorter: 'quality' },
            //         6: { sorter: 'eps' },
            //         7: { sorter: 'digit' },
            //         8: { filter: 'parsed' },
            //         10: { filter: 'parsed' }
            //     },
            //     widgetOptions: {
            //         filter_columnFilters: true, // eslint-disable-line camelcase
            //         filter_hideFilters: true, // eslint-disable-line camelcase
            //         filter_saveFilters: true, // eslint-disable-line camelcase
            //         filter_functions: { // eslint-disable-line camelcase
            //             5(e, n, f) { // eslint-disable-line complexity
            //                 let test = false;
            //                 const pct = Math.floor((n % 1) * 1000);
            //                 if (f === '') {
            //                     test = true;
            //                 } else {
            //                     let result = f.match(/(<|<=|>=|>)\s+(\d+)/i);
            //                     if (result) {
            //                         if (result[1] === '<') {
            //                             if (pct < parseInt(result[2], 10)) {
            //                                 test = true;
            //                             }
            //                         } else if (result[1] === '<=') {
            //                             if (pct <= parseInt(result[2], 10)) {
            //                                 test = true;
            //                             }
            //                         } else if (result[1] === '>=') {
            //                             if (pct >= parseInt(result[2], 10)) {
            //                                 test = true;
            //                             }
            //                         } else if (result[1] === '>') {
            //                             if (pct > parseInt(result[2], 10)) {
            //                                 test = true;
            //                             }
            //                         }
            //                     }

            //                     result = f.match(/(\d+)\s(-|to)\s+(\d+)/i);
            //                     if (result) {
            //                         if ((result[2] === '-') || (result[2] === 'to')) {
            //                             if ((pct >= parseInt(result[1], 10)) && (pct <= parseInt(result[3], 10))) {
            //                                 test = true;
            //                             }
            //                         }
            //                     }

            //                     result = f.match(/(=)?\s?(\d+)\s?(=)?/i);
            //                     if (result) {
            //                         if ((result[1] === '=') || (result[3] === '=')) {
            //                             if (parseInt(result[2], 10) === pct) {
            //                                 test = true;
            //                             }
            //                         }
            //                     }

            //                     if (!isNaN(parseFloat(f)) && isFinite(f)) {
            //                         if (parseInt(f, 10) === pct) {
            //                             test = true;
            //                         }
            //                     }
            //                 }
            //                 return test;
            //             }
            //         },
            //         columnSelector_mediaquery: false // eslint-disable-line camelcase
            //     },
            //     sortStable: true,
            //     sortAppend: [[2, 0]]
            // }).bind('sortEnd', () => {
            //     imgLazyLoad.handleScroll();
            // }).bind('filterEnd', () => {
            //     imgLazyLoad.handleScroll();
            // });

            // $('.show-grid').imagesLoaded(() => {
            //     this.initializePosterSizeSlider();
            //     $('.loading-spinner').hide();
            //     $('.show-grid').show().isotope({
            //         itemSelector: '.show-container',
            //         sortBy: stateLayout.posterSortby,
            //         sortAscending: stateLayout.posterSortdir,
            //         layoutMode: 'masonry',
            //         masonry: {
            //             isFitWidth: true
            //         },
            //         getSortData: {
            //             name(itemElem) {
            //                 const name = $(itemElem).attr('data-name') || '';
            //                 return (stateLayout.sortArticle ? name : name.replace(/^((?:The|A|An)\s)/i, '')).toLowerCase();
            //             },
            //             network: '[data-network]',
            //             date(itemElem) {
            //                 const date = $(itemElem).attr('data-date');
            //                 return (date.length && parseInt(date, 10)) || Number.POSITIVE_INFINITY;
            //             },
            //             progress(itemElem) {
            //                 const progress = $(itemElem).attr('data-progress');
            //                 return (progress.length && parseInt(progress, 10)) || Number.NEGATIVE_INFINITY;
            //             },
            //             indexer(itemElem) {
            //                 const indexer = $(itemElem).attr('data-indexer');
            //                 if (indexer === undefined) {
            //                     return Number.NEGATIVE_INFINITY;
            //                 }
            //                 return (indexer.length && parseInt(indexer, 10)) || Number.NEGATIVE_INFINITY;
            //             }
            //         }
            //     }).on('layoutComplete arrangeComplete removeComplete', () => {
            //         imgLazyLoad.update();
            //         imgLazyLoad.handleScroll();
            //     });

            //     // When posters are small enough to not display the .show-details
            //     // table, display a larger poster when hovering.
            //     let posterHoverTimer = null;
            //     $('.show-container').on('mouseenter', function() {
            //         const poster = $(this);
            //         if (poster.find('.show-details').css('display') !== 'none') {
            //             return;
            //         }
            //         posterHoverTimer = setTimeout(() => {
            //             posterHoverTimer = null;
            //             $('#posterPopup').remove();
            //             const popup = poster.clone().attr({
            //                 id: 'posterPopup'
            //             });
            //             const origLeft = poster.offset().left;
            //             const origTop = poster.offset().top;
            //             popup.css({
            //                 position: 'absolute',
            //                 margin: 0,
            //                 top: origTop,
            //                 left: origLeft
            //             });
            //             popup.find('.show-details').show();
            //             popup.on('mouseleave', function() {
            //                 $(this).remove();
            //             });
            //             popup.css({ zIndex: '9999' });
            //             popup.appendTo('body');

            //             const height = 438;
            //             const width = 250;
            //             let newTop = (origTop + (poster.height() / 2)) - (height / 2);
            //             let newLeft = (origLeft + (poster.width() / 2)) - (width / 2);

            //             // Make sure the popup isn't outside the viewport
            //             const margin = 5;
            //             const scrollTop = $(window).scrollTop();
            //             const scrollLeft = $(window).scrollLeft();
            //             const scrollBottom = scrollTop + $(window).innerHeight();
            //             const scrollRight = scrollLeft + $(window).innerWidth();
            //             if (newTop < scrollTop + margin) {
            //                 newTop = scrollTop + margin;
            //             }
            //             if (newLeft < scrollLeft + margin) {
            //                 newLeft = scrollLeft + margin;
            //             }
            //             if (newTop + height + margin > scrollBottom) {
            //                 newTop = scrollBottom - height - margin;
            //             }
            //             if (newLeft + width + margin > scrollRight) {
            //                 newLeft = scrollRight - width - margin;
            //             }

            //             popup.animate({
            //                 top: newTop,
            //                 left: newLeft,
            //                 width: 250,
            //                 height: 438
            //             });
            //         }, 300);
            //     }).on('mouseleave', () => {
            //         if (posterHoverTimer !== null) {
            //             clearTimeout(posterHoverTimer);
            //         }
            //     });
            //     imgLazyLoad.update();
            //     imgLazyLoad.handleScroll();
            // });

            // $('#popover').popover({
            //     placement: 'bottom',
            //     html: true, // Required if content has HTML
            //     content: '<div id="popover-target"></div>'
            // }).on('shown.bs.popover', () => { // Bootstrap popover event triggered when the popover opens
            //     // call this function to copy the column selection code into the popover
            //     $.tablesorter.columnSelector.attachTo($('#showListTableSeries'), '#popover-target');
            //     if (stateLayout.animeSplitHome) {
            //         $.tablesorter.columnSelector.attachTo($('#showListTableAnime'), '#popover-target');
            //     }
            // });

            // $('#poster-container').sortable({
            //     appendTo: document.body,
            //     axis: 'y',
            //     items: '> .show-grid',
            //     scroll: false,
            //     tolerance: 'pointer',
            //     helper: 'clone',
            //     handle: 'button.move-show-list',
            //     cancel: '',
            //     sort(event, ui) {
            //         const draggedItem = $(ui.item);
            //         const margin = 1.5;

            //         if (ui.position.top !== ui.originalPosition.top) {
            //             if (ui.position.top > ui.originalPosition.top * margin) {
            //                 // Move to bottom
            //                 setTimeout(() => {
            //                     $(draggedItem).appendTo('#poster-container');
            //                     return false;
            //                 }, 400);
            //             }
            //             if (ui.position.top < ui.originalPosition.top / margin) {
            //                 // Move to top
            //                 setTimeout(() => {
            //                     $(draggedItem).prependTo('#poster-container');
            //                     return false;
            //                 }, 400);
            //             }
            //         }
            //     },
            //     async update(event) {
            //         const showListOrder = $(event.target.children).map((index, el) => {
            //             return $(el).data('list');
            //         });

            //         const layout = {
            //             show: {
            //                 showListOrder: showListOrder.toArray()
            //             }
            //         };

            //         try {
            //             await setConfig({ section: 'main', config: { layout } });
            //             $snotify.success(
            //                 'Saved Home poster list type order',
            //                 'Saved',
            //                 { timeout: 5000 }
            //             );
            //         } catch (error) {
            //             $snotify.error(
            //                 'Error while trying to save home poster list type order',
            //                 'Error'
            //             );
            //     }
            //     }
            // });
        // }; // END initializePage()

        // Vue Stuff (prevent race condition issues)
        const unwatch = this.$watch('config.rootDirs', () => {
            unwatch();

            const { config } = this;
            const { rootDirs, selectedRootIndex } = config;

            if (rootDirs) {
                const backendDirs = rootDirs.slice(1);
                if (backendDirs.length >= 2) {
                    this.$nextTick(() => {
                        $('#showRoot').show();
                        const item = ['All Folders'];
                        const rootDirOptions = item.concat(backendDirs);
                        $.each(rootDirOptions, (i, item) => {
                            $('#showRootDir').append($('<option>', {
                                value: i - 1,
                                text: item
                            }));
                        });
                        $('select#showRootDir').prop('selectedIndex', selectedRootIndex + 1);
                    });
                } else {
                    $('#showRoot').hide();
                }
            }
        });

        // window.addEventListener('load', initializePage, { once: true });
    }
};
</script>

<style>
</style>
