<template>
    <div name="poster-container-row" class="row">
        <div name="poster-container-col" class="col-md-12">
            <isotope :ref="`isotope-${listTitle}`" :list="sortedShows" :id="`isotope-container-${listTitle}`" class="isoDefault" :item-selector="'show-container'" :options="option" v-images-loaded:on.progress="updateLayout">
                <div v-for="show in sortedShows" :key="show.id[show.indexer]" :id="`show${show.id[show.indexer]}`" :data-name="show.title" :data-date="show.airDate" :data-network="show.network" :data-indexer="show.indexer">
                    <div class="overlay-container">
                        <div class="background-image">
                            <img src="images/poster-back-dark.png">
                        </div>
                        <div class="poster-overlay">
                            <app-link href="`home/displayShow?indexername=${props.row.indexer}&seriesid=${props.row.id[props.row.indexer]}`">
                                <asset default="images/poster.png" :show-slug="show.id.slug" :lazy="false" type="posterThumb" cls="show-image" :link="false"></asset>
                            </app-link>
                        </div>
                    </div>
                    <div class="show-poster-footer row">
                        <div class="col-md-12">
                            <div class="progressbar hidden-print" style="position:relative;" :data-show-id="show.id[show.indexer]" data-progress-percentage="${progressbar_percent}"></div>
                            <div class="show-title">
                                <div class="ellipsis">{{show.title}}</div>
                                <!-- if get_xem_numbering_for_show(cur_show, refresh_data=False): -->
                                <div class="xem">
                                    <img src="images/xem.png" width="16" height="16" />
                                </div>
                                <!--  endif -->
                            </div>
                            <div class="show-date">
                    <!-- if cur_airs_next:
                        < ldatetime = sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(cur_airs_next, cur_show.airs, cur_show.network)) >
                        <
                            try:
                                out = str(sbdatetime.sbdatetime.sbfdate(ldatetime))
                            except ValueError:
                                out = 'Invalid date'
                                pass
                        >
                            ${out}
                        else:
                        <
                        output_html = '?'
                        display_status = cur_show.status
                        if None is not display_status:
                            if 'nded' not in display_status and 1 == int(cur_show.paused):
                                output_html = 'Paused'
                            elif display_status:
                                output_html = display_status
                        ${output_html}
                        endif -->
                            </div>
                            <div class="show-details">
                                <table :class="{fanartOpacity: stateLayout.fanartBackground}" class="show-details" width="100%" cellspacing="1" border="0" cellpadding="0">
                                    <tr>
                                        <td class="show-table">
                                            <span class="show-dlstats" :title="`Downloaded: ${show.stats.episodes.downloaded}${!show.stats.episodes.snatched ? '' : '; Snatched:' + show.stats.episodes.snatched}; Total: ${show.stats.episodes.total}`">
                                                {{`${show.stats.episodes.downloaded}${!show.stats.episodes.snatched ? '' : '+' + show.stats.episodes.snatched} / ${show.stats.episodes.total}`}}
                                            </span>
                                        </td>
                                        <td class="show-table">
                                            <span v-if="show.network" :title="show.network">
                                                <asset default="images/network/nonetwork.png" :show-slug="show.id.slug" :lazy="false" type="network" cls="show-network-image" :link="false" :alt="show.network" :title="show.network">
                                            </span>
                                            <span v-else title="No Network"><img class="show-network-image" src="images/network/nonetwork.png" alt="No Network" title="No Network" /></span>
                                        </td>
                                        <td class="show-table">
                                            <quality-pill :allowed="show.config.qualities.allowed" :preferred="show.config.qualities.preferred" :override="{ class: 'show-quality' }" show-title/>
                                        </td>
                                    </tr>
                                </table>
                            </div>
                        </div> <!-- col -->
                    </div> <!-- show-poster-footer -->
                </div>
            </isotope>
        </div>
    </div> 
</template>
<script>
import { mapGetters, mapState } from 'vuex';
import pretty from 'pretty-bytes';
import { Asset } from '../helpers';
import { AppLink } from '../helpers';
import { ProgressBar } from '../helpers';
import { QualityPill } from '../helpers';
import isotope from 'vueisotope';
import imagesLoaded from 'vue-images-loaded';

export default {
    name: 'poster',
    directives: {
        imagesLoaded
    },
    components: {
        Asset,
        AppLink,
        ProgressBar,
        QualityPill,
        isotope
    },
    props: {
        layout: {
            validator: val => val === null || typeof val === 'string',
            required: true
        },
        shows: {
            type: Array,
            required: true
        },
        listTitle: {
            type: String
        },
        header: {
            type: Boolean
        }
    },
    data() {
        return {
            // Isotope stuff
            itemSelector: '.show-container',
            selected: null,
            option: {
                getSortData: {
                    id: row => row.id.slug,
                    name: 'title',
                    date: 'nextAirDate',
                    network: 'network',
                    progress: row => {
                        if (!row.stats.episodes.total) {
                            return row.stats.episodes.total;
                        }
                        return Math.round(row.stats.episodes.downloaded / row.stats.episodes.total * 100)
                    },
                    indexer: row => {
                            const { indexers } = this;
                            return indexers[row.indexer].id
                        }
                },
                getFilterData: {
                    filterByText: item => {
                        const { stateLayout } = this;
                        const { posterFilterByName } = stateLayout;
                        return item.title.toLowerCase().includes(posterFilterByName.toLowerCase());
                    }
                },
                sortBy: () => this.posterSortBy,
                layoutMode: 'fitRows',
                sortAscending: () => this.posterSortDir
            }
        };
    },
    computed: {
        ...mapState({
            config: state => state.config,
            indexerConfig: state => state.indexers.indexers,
            sortArticle: state => state.layout.sortArticle ,
            posterSortBy: state => state.layout.posterSortby,
            posterSortDir: state => state.layout.posterSortdir,
            stateLayout: state => state.layout,
            indexers: state => state.indexers.indexers,
            posterFilterByName: state => state.layout.posterFilterByName
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        }),
        sortedShows() {
            const { shows, sortArticle } = this;
            const removeArticle = str => sortArticle ? str.replace(/^((?:A(?!\s+to)n?)|The)\s/i, '') : str;
            return shows.concat().sort((a, b) => removeArticle(a.title).toLowerCase().localeCompare(removeArticle(b.title).toLowerCase()));
        }
    },
    methods: {
        prettyBytes: bytes => pretty(bytes),
        showIndexerUrl(show) {
            const { indexerConfig } = this;
            if (!show.indexer) {
                return;
            }

            const id = show.id[show.indexer];
            const indexerUrl = indexerConfig[show.indexer].showUrl;
            return `${indexerUrl}${id}`;
        },
        parsePrevDateFn(row) {
            const { fuzzyParseDateTime } = this;
            if (row.prevAirDate) {
                console.log(`Calculating time for show ${row.title} prev date: ${row.prevAirDate}`);
                return fuzzyParseDateTime(row.prevAirDate);
            };
            return '';
        },
        parseNextDateFn(row) {
            const { fuzzyParseDateTime } = this;
            if (row.nextAirDate) {
                console.log(`Calculating time for show ${row.title} next date: ${row.nextAirDate}`);
                return fuzzyParseDateTime(row.nextAirDate)
            };
            return '';
        },
        isotopeLayout() {
            const { imgLazyLoad } = this;

            console.log('isotope Layout loaded');
            imgLazyLoad.update();
            // imgLazyLoad.handleScroll();
        },
        updateLayout() {
            const { listTitle } = this;
            this.$refs[`isotope-${listTitle}`].layout();
        },
        filter(key) {
            const { listTitle } = this;
            
        }
    },
    watch: {
        posterSortBy(key) {
            const { listTitle } = this;
            this.$refs[`isotope-${listTitle}`].sort(key);
        },
        posterSortDir(value) {
            const { listTitle, option } = this;
            this.option.sortAscending = Boolean(value);
            this.$refs[`isotope-${listTitle}`].arrange(option);
        },
        posterFilterByName(value) {
            const { listTitle } = this;
            this.$refs[`isotope-${listTitle}`].filter('filterByText');
        }
    }
}
</script>
<style>
.show-container {
    display: inline-block;
    margin: 4px;
    background-color: rgb(243, 243, 243);
    border: 5px solid rgb(243, 243, 243);
    overflow: hidden;
    box-shadow: 1px 1px 3px 0 rgba(0, 0, 0, 0.31);
}

.show-dlstats {
    font-size: 11px;
    text-align: left;
    display: block;
    margin-left: 4px;
}

.show-quality {
    font-size: 11px;
    text-align: right;
    display: block;
    margin-right: 4px;
}

.posterview {
    margin: 0 auto;
    position: relative;
}

.show-image {
    max-width: 200px;
}

/* Used by isotope scaling */
.show-image {
    max-width: 100%;
    overflow: hidden;
    border: 1px solid rgb(136, 136, 136);
}

.background-image img {
    max-width: 200px;
    overflow: hidden;
}

.poster-overlay {
    position: absolute;
}

.show-container .ui-progressbar {
    height: 7px !important;
    top: -2px;
}

.show-container .ui-corner-all,
.ui-corner-bottom,
.ui-corner-right,
.ui-corner-br {
    border-bottom-right-radius: 0;
}

.show-container .ui-corner-all,
.ui-corner-bottom,
.ui-corner-left,
.ui-corner-bl {
    border-bottom-left-radius: 0;
}

.show-container .ui-corner-all,
.ui-corner-top,
.ui-corner-right,
.ui-corner-tr {
    border-top-right-radius: 0;
}

.show-container .ui-corner-all,
.ui-corner-top,
.ui-corner-left,
.ui-corner-tl {
    border-top-left-radius: 0;
}

.show-container .ui-widget-content {
    border-top: 1px solid rgb(17, 17, 17);
    border-bottom: 1px solid rgb(17, 17, 17);
    border-left: 0;
    border-right: 0;
}

.ui-progressbar .progress-20 {
    border: none;
}

.show-container .progress-20,
.show-container .progress-40,
.show-container .progress-60,
.show-container .progress-80 {
    border-radius: 0;
    height: 7px;
}

.overlay-container {
    display: flex;
}
</style>