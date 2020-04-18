<template>
        <isotope ref="filteredShows" :list="sortedShows" id="isotope-container" class="isoDefault" :options="option" @layout="isotopeLayout($event)">
            <div v-for="show in sortedShows" :key="show.id[show.indexer]" class="show-container" :id="`show${show.id[show.indexer]}`" :data-name="show.title" :data-date="show.airDate" :data-network="show.network" :data-indexer="show.indexer">
                <div class="aligner">
                    <div class="background-image">
                        <img src="images/poster-back-dark.png"/>
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
                            <table class="show-details ${'fanartOpacity' if app.FANART_BACKGROUND else ''}" width="100%" cellspacing="1" border="0" cellpadding="0">
                                <tr>
                                    <td class="show-table">
                                        <span class="show-dlstats" title="${download_stat_tip}">STATS HERE</span>
                                    </td>
                                    <td class="show-table">
                                    <!--  if cur_show.network: -->
                                        <span v-if="show.network" :title="show.network">
                                            <asset default="images/network/nonetwork.png" :show-slug="show.id.slug" :lazy="false" type="network" cls="show-network-image" :link="false" :alt="show.network" :title="show.network"></asset>
                                        </span>
                                        <span v-else title="No Network"><img class="show-network-image" src="images/network/nonetwork.png" alt="No Network" title="No Network" /></span>
                                    <!--  endif -->
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
</template>
<script>
import { mapGetters, mapState } from 'vuex';
import pretty from 'pretty-bytes';
import { Asset } from '../helpers';
import { AppLink } from '../helpers';
import { ProgressBar } from '../helpers';
import { QualityPill } from '../helpers';
import { VueGoodTable } from 'vue-good-table';
import isotope from 'vueisotope';

export default {
    name: 'poster',
    components: {
        Asset,
        AppLink,
        ProgressBar,
        QualityPill,
        VueGoodTable,
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
        },
        sortArticle: {
            type: Boolean
        }
    },
    data() {
        return {
            // Isotope stuff
            selected: null,
            option: {
                getSortData: {
                    id: itemElem => itemElem.id.slug,
                    title: 'title'
                },
                getFilterData: {
                    filterByText: itemElem => {
                        return itemElem.title.toLowerCase().includes(this.filterShows.toLowerCase());
                    }
                },
                sortBy: 'id',
                layoutMode: 'fitRows',
                sortAscending: false
            }
        }
    },
    computed: {
        ...mapState({
            config: state => state.config,
            indexerConfig: state => state.indexers.indexers
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        }),
        sortedShows() {
            const removeArticle = str => this.sortArticle ? str.replace(/^((?:A(?!\s+to)n?)|The)\s/i, '') : str;
            return this.shows.concat().sort((a, b) => removeArticle(a.title).toLowerCase().localeCompare(removeArticle(b.title).toLowerCase()));
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
                return fuzzyParseDateTime(row.prevAirDate)
            } else {
                return ''
            }
        },
        parseNextDateFn(row) {
            const { fuzzyParseDateTime } = this;
            if (row.nextAirDate) {
                console.log(`Calculating time for show ${row.title} next date: ${row.nextAirDate}`);
                return fuzzyParseDateTime(row.nextAirDate)
            } else {
                return ''
            }
        },
        isotopeLayout() {
            const { imgLazyLoad } = this;

            console.log('isotope Layout loaded');
            imgLazyLoad.update();
            // imgLazyLoad.handleScroll();
        },
    }
}
</script>
