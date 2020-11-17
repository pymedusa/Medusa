<template>
    <div name="poster-container-row" class="row">
        <div name="poster-container-col" class="col-md-12">
            <isotope :ref="`isotope-${listTitle}`" :list="showsReady" :id="`isotope-container-${listTitle}`" :item-selector="'show-container'" :options="option" v-images-loaded:on.always="updateLayout">
                <div v-for="show in showsReady" :key="show.id.slug" :id="show.id.slug" :style="showContainerStyle" :data-name="show.title" :data-date="show.airDate" :data-network="show.network" :data-indexer="show.indexer">
                    <div class="overlay-container">
                        <div class="background-image">
                            <img src="images/poster-back-dark.png">
                        </div>
                        <div class="poster-overlay">
                            <app-link :href="`home/displayShow?indexername=${show.indexer}&seriesid=${show.id[show.indexer]}`">
                                <asset default-src="images/poster.png" :show-slug="show.id.slug" lazy type="posterThumb" cls="show-image" :link="false" />
                            </app-link>
                        </div>
                    </div>
                    <div class="show-poster-footer row">
                        <div class="col-md-12">
                            <progress-bar :percentage="show.stats.tooltip.percentage" />
                            <div class="show-title">
                                <div class="ellipsis">{{show.title}}</div>
                                <div v-if="show.xemNumbering.length > 0" class="xem">
                                    <img src="images/xem.png" width="16" height="16">
                                </div>
                                <!--  endif -->
                            </div>
                            <div class="show-date">
                                {{dateOrStatus(show)}}
                            </div>
                            <div v-show="fontSize !== null" class="show-details">
                                <table :class="{fanartOpacity: stateLayout.fanartBackground}" class="show-details" width="100%" cellspacing="1" border="0" cellpadding="0">
                                    <tr>
                                        <td class="show-table">
                                            <span class="show-dlstats" :style="{fontSize}" :title="`Downloaded: ${show.stats.episodes.downloaded}${!show.stats.episodes.snatched ? '' : '; Snatched:' + show.stats.episodes.snatched}; Total: ${show.stats.episodes.total}`">
                                                {{`${show.stats.episodes.downloaded}${!show.stats.episodes.snatched ? '' : '+' + show.stats.episodes.snatched} / ${show.stats.episodes.total}`}}
                                            </span>
                                        </td>
                                        <td class="show-table">
                                            <span v-if="show.network" :title="show.network">
                                                <asset default-src="images/network/nonetwork.png" :show-slug="show.id.slug" type="network" cls="show-network-image" :link="false" :alt="show.network" :title="show.network" :imgWidth="logoWidth" />
                                            </span>
                                            <span v-else title="No Network"><img class="show-network-image" src="images/network/nonetwork.png" alt="No Network" title="No Network"></span>
                                        </td>
                                        <td class="show-table">
                                            <quality-pill :allowed="show.config.qualities.allowed" :preferred="show.config.qualities.preferred" :override="{ class: 'show-quality', style: 'test' }" show-title />
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
import { AppLink, Asset, ProgressBar, QualityPill } from '../helpers';
import Isotope from 'vueisotope';
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
        Isotope
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
                    name: row => {
                        const { stateLayout } = this;
                        const { sortArticle } = stateLayout;

                        if (sortArticle) {
                            return row.title;
                        }

                        return row.title.replace(/^((?:a(?!\s+to)n?)|the)\s/i, '').toLowerCase();
                    },
                    date: row => {
                        const { maxNextAirDate } = this;
                        if (row.nextAirDate && Date.parse(row.nextAirDate) > Date.now()) {
                            return Date.parse(row.nextAirDate) - Date.now();
                        }

                        if (row.prevAirDate) {
                            return maxNextAirDate + Date.now() - Date.parse(row.prevAirDate);
                        }

                        return Date.now();
                    },
                    network: 'network',
                    progress: row => {
                        if (!row.stats) {
                            return 0;
                        }

                        return Math.round(row.stats.episodes.downloaded / row.stats.episodes.total * 100);
                    },
                    indexer: row => {
                        const { indexers } = this;
                        return indexers.indexers[row.indexer].id;
                    }
                },
                sortBy: () => this.posterSortBy,
                layoutMode: 'fitRows',
                sortAscending: () => this.posterSortDir
            },
            fontSize: null,
            logoWidth: null,
            borderRadius: null,
            borderWidth: null,
            isotopeLoaded: false,
            imgLazyLoad: null,
            filterByTitle: ''
        };
    },
    computed: {
        ...mapState({
            config: state => state.config.general,
            stateLayout: state => state.config.layout,
            indexers: state => state.config.indexers,
            // Need to map these computed, as we need them in the $watch.
            posterSortBy: state => state.config.layout.posterSortby,
            posterSortDir: state => state.config.layout.posterSortdir,
            posterSize: state => state.config.layout.local.posterSize,
            currentShowTab: state => state.config.layout.local.currentShowTab,
            showFilterByName: state => state.config.layout.local.showFilterByName
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        }),
        showsReady() {
            const { shows, maxNextAirDate } = this;
            if (shows.length === 0 || !maxNextAirDate) {
                return [];
            }

            return shows;
        },
        showContainerStyle() {
            const { posterSize, borderWidth, borderRadius } = this;
            return {
                width: posterSize + 'px',
                borderWidth: borderWidth + 'px',
                borderRadius: borderRadius + 'px'
            };
        },
        maxNextAirDate() {
            const { shows } = this;
            return Math.max(...shows.filter(show => show.nextAirDate).map(show => Date.parse(show.nextAirDate)));
        }
    },
    methods: {
        prettyBytes: bytes => pretty(bytes),
        showIndexerUrl(show) {
            const { indexers } = this;
            if (!show.indexer) {
                return;
            }

            const id = show.id[show.indexer];
            const indexerUrl = indexers.indexers[show.indexer].showUrl;
            return `${indexerUrl}${id}`;
        },
        parsePrevDateFn(row) {
            const { fuzzyParseDateTime } = this;
            if (row.prevAirDate) {
                console.log(`Calculating time for show ${row.title} prev date: ${row.prevAirDate}`);
                return fuzzyParseDateTime(row.prevAirDate);
            }
            return '';
        },
        parseNextDateFn(row) {
            const { fuzzyParseDateTime } = this;
            if (row.nextAirDate) {
                console.log(`Calculating time for show ${row.title} next date: ${row.nextAirDate}`);
                return fuzzyParseDateTime(row.nextAirDate);
            }
            return '';
        },
        calculateSize() {
            const { posterSize } = this;

            if (posterSize < 125) { // Small
                this.fontSize = null;
                this.borderRadius = 3;
                this.borderWidth = 4;
            } else if (posterSize < 175) { // Medium
                this.fontSize = 9;
                this.logoWidth = 40;
                this.borderRadius = 4;
                this.borderWidth = 5;
            } else { // Large
                this.fontSize = 11;
                this.logoWidth = 50;
                this.borderRadius = 6;
                this.borderWidth = 6;
            }
        },
        updateLayout() {
            const {
                calculateSize,
                listTitle, posterSortBy,
                posterSortDir
            } = this;
            this.isotopeLoaded = true;
            calculateSize();
            // If we can't find a layout, bail out, as there is nothing to arrange.
            if (this.$refs[`isotope-${listTitle}`] === undefined) {
                return;
            }
            // Render layout (for sizing)
            this.$refs[`isotope-${listTitle}`].layout();
            // Arrange & Sort
            this.$refs[`isotope-${listTitle}`].arrange({ sortBy: posterSortBy, sortAscending: posterSortDir });
            console.log('isotope Layout loaded');
        },
        dateOrStatus(show) {
            if (show.nextAirDate) {
                const { fuzzyParseDateTime } = this;
                return fuzzyParseDateTime(show.nextAirDate);
            }
            if (!show.status.includes('nded') && show.config.paused) {
                return 'Paused';
            }
            return show.status;
        }
    },
    watch: {
        posterSortBy(key) {
            const { listTitle } = this;
            this.$refs[`isotope-${listTitle}`].sort(key);
        },
        posterSortDir(value) {
            const { listTitle, posterSortBy } = this;
            this.$refs[`isotope-${listTitle}`].arrange({ sortBy: posterSortBy, sortAscending: value });
        },
        posterSize(oldSize, newSize) {
            const { calculateSize, isotopeLoaded, listTitle } = this;
            if (!isotopeLoaded || oldSize === newSize) {
                return;
            }
            calculateSize();
            this.$nextTick(() => {
                this.$refs[`isotope-${listTitle}`].arrange();
            });
        },
        currentShowTab() {
            const { isotopeLoaded, listTitle } = this;
            if (!isotopeLoaded) {
                return;
            }

            this.$nextTick(() => {
                this.$refs[`isotope-${listTitle}`].arrange();
            });
        },
        showFilterByName(value) {
            const { $refs, listTitle } = this;

            const allContainers = $refs[`isotope-${listTitle}`].$el.querySelectorAll('.show-container');

            for (const container of allContainers) {
                if (container.textContent.toLowerCase().includes(value.toLowerCase())) {
                    container.classList.remove('hide');
                } else {
                    container.classList.add('hide');
                }
            }
        }
    }
};
</script>
<style scoped>
.show-container {
    display: inline-block;
    margin: 4px;
    border-width: 5px;
    border-style: solid;
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

/* Used by isotope scaling */
.show-image {
    max-width: 100%;
    overflow: hidden;
    border: 1px solid rgb(136, 136, 136);
}

.background-image img {
    width: 100%;
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
    align-items: baseline;
}
</style>
