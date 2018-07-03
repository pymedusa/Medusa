<%inherit file="/layouts/main.mako"/>
<%!
    from random import choice

    from medusa import app
%>
<%block name="scripts">
<script type="text/javascript" src="js/ajax-episode-search.js?${sbPID}"></script>
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        store,
        router,
        metaInfo: {
            title: 'Schedule'
        },
        data() {
            return {
                header: 'Schedule'
            };
        },
        computed: Object.assign(
            store.mapState(['shows']),
            {
                layout: {
                    get() {
                        const { config } = this;
                        return config.layout.schedule;
                    },
                    set(layout) {
                        const { $store } = this;
                        const page = 'schedule';
                        $store.dispatch('setLayout', { page, layout });
                    }
                }
            }
        ),
        mounted() {
            const { $store, $route } = this;
            // $store.dispatch('getShows');

            const unwatch = this.$watch('layout', () => {
                unwatch();
                const { config, layout } = this;
                if (layout === 'list') {
                    const sortCodes = {
                        date: 0,
                        show: 2,
                        network: 5
                    };
                    const sort = config.comingEpsSort;
                    const sortList = (sort in sortCodes) ? [[sortCodes[sort], 0]] : [[0, 0]];

                    $('#showListTable:has(tbody tr)').tablesorter({
                        widgets: ['stickyHeaders', 'filter', 'columnSelector', 'saveSort'],
                        sortList,
                        textExtraction: {
                            0: node => $(node).find('time').attr('datetime'),
                            1: node => $(node).find('time').attr('datetime'),
                            7: node => $(node).find('span').text().toLowerCase(),
                            8: node => $(node).find('a[data-indexer-name]').attr('data-indexer-name')
                        },
                        headers: {
                            0: { sorter: 'realISODate' },
                            1: { sorter: 'realISODate' },
                            2: { sorter: 'loadingNames' },
                            4: { sorter: 'loadingNames' },
                            7: { sorter: 'quality' },
                            8: { sorter: 'text' },
                            9: { sorter: false, filter: false }
                        },
                        widgetOptions: {
                            filter_columnFilters: true, // eslint-disable-line camelcase
                            filter_hideFilters: true, // eslint-disable-line camelcase
                            filter_saveFilters: true, // eslint-disable-line camelcase
                            columnSelector_mediaquery: false // eslint-disable-line camelcase
                        }
                    });

                    $.ajaxEpSearch();
                }

                if (['banner', 'poster'].includes(layout)) {
                    $.ajaxEpSearch({
                        size: 16,
                        loadingImage: 'loading16' + MEDUSA.config.themeSpinner + '.gif'
                    });
                    $('.ep_summary').hide();
                    $('.ep_summaryTrigger').on('click', function() {
                        $(this).next('.ep_summary').slideToggle('normal', function() {
                            $(this).prev('.ep_summaryTrigger').prop('src', function(i, src) {
                                return $(this).next('.ep_summary').is(':visible') ? src.replace('plus', 'minus') : src.replace('minus', 'plus');
                            });
                        });
                    });
                }

                $('#popover').popover({
                    placement: 'bottom',
                    html: true, // Required if content has HTML
                    content: '<div id="popover-target"></div>'
                }).on('shown.bs.popover', () => { // Bootstrap popover event triggered when the popover opens
                    // call this function to copy the column selection code into the popover
                    $.tablesorter.columnSelector.attachTo($('#showListTable'), '#popover-target');
                });
            });
        }
    });
};
</script>
</%block>

<%block name="content">
<% random_series = choice(results) if results else '' %>
<input type="hidden" id="background-series-slug" value="${choice(results)['series_slug'] if results else ''}" />

<div class="row">
    <div class="col-md-12">
        <h1 class="header">{{header}}</h1>
    </div>
</div>

<div class="row">
    <div class="col-md-12">
        <div class="key pull-left">
            <template v-if="layout !== 'calendar'">
                <b>Key:</b>
                <span class="listing-key listing-overdue">Missed</span>
                <span class="listing-key listing-current">Today</span>
                <span class="listing-key listing-default">Soon</span>
                <span class="listing-key listing-toofar">Later</span>
            </template>
            <app-link class="btn-medusa btn-inline forceBacklog" href="webcal://${sbHost}:${sbHttpPort}/calendar">
            <i class="icon-calendar icon-white"></i>Subscribe</app-link>
        </div>

        <div class="pull-right">
            <div class="show-option">
                <span>View Paused:
                    <select name="viewpaused" class="form-control form-control-inline input-sm" onchange="location = this.options[this.selectedIndex].value;">
                        <option value="schedule/toggleScheduleDisplayPaused" ${'selected="selected"' if not bool(app.COMING_EPS_DISPLAY_PAUSED) else ''}>Hidden</option>
                        <option value="schedule/toggleScheduleDisplayPaused" ${'selected="selected"' if app.COMING_EPS_DISPLAY_PAUSED else ''}>Shown</option>
                    </select>
                </span>
            </div>
            <div class="show-option">
                <span>Layout:
                    <select v-model="layout" name="layout" class="form-control form-control-inline input-sm">
                        <option value="poster" ${'selected="selected"' if app.COMING_EPS_LAYOUT == 'poster' else ''}>Poster</option>
                        <option value="calendar" ${'selected="selected"' if app.COMING_EPS_LAYOUT == 'calendar' else ''}>Calendar</option>
                        <option value="banner" ${'selected="selected"' if app.COMING_EPS_LAYOUT == 'banner' else ''}>Banner</option>
                        <option value="list" ${'selected="selected"' if app.COMING_EPS_LAYOUT == 'list' else ''}>List</option>
                    </select>
                </span>
            </div>
            <div v-if="layout === 'list'" class="show-option">
                <button id="popover" type="button" class="btn-medusa btn-inline">Select Columns <b class="caret"></b></button>
            </div>
            <!-- Calendar sorting is always by date -->
            <div v-else-if="layout !== 'calendar'" class="show-option">
                <span>Sort By:
                    <select name="sort" class="form-control form-control-inline input-sm" onchange="location = 'schedule/setScheduleSort/?sort=' + this.options[this.selectedIndex].value;">
                        <option value="date" ${'selected="selected"' if app.COMING_EPS_SORT == 'date' else ''}>Date</option>
                        <option value="network" ${'selected="selected"' if app.COMING_EPS_SORT == 'network' else ''}>Network</option>
                        <option value="show" ${'selected="selected"' if app.COMING_EPS_SORT == 'show' else ''}>Show</option>
                    </select>
                </span>
            </div>
        </div>
    </div>
</div>

<div class="horizontal-scroll">
    <%include file="/partials/schedule/${layout}.mako"/>
</div> <!-- end horizontal scroll -->
<div class="clearfix"></div>
</%block>
