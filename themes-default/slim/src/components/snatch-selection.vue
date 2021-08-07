<template>
    <div id="snatch-selection-template">
        <vue-snotify />
        <backstretch v-if="show.id.slug" :slug="show.id.slug" :key="show.id.slug" />

        <show-header type="snatch-selection"
                     ref="show-header"
                     :slug="showSlug"
                     :manual-search-type="manualSearchType"
                     @update-overview-status="filterByOverviewStatus = $event"
        />

        <show-history v-show="show" class="show-history vgt-table-styling" v-bind="{ show, season, episode }" :key="`history-${show.id.slug}-${season}-${episode || ''}`" />

        <show-results v-show="show" class="table-layout vgt-table-styling" v-bind="{ show, season, episode }" :key="`results-${show.id.slug}-${season}-${episode || ''}`" />

    </div>
</template>

<script>
import { mapState, mapGetters, mapActions } from 'vuex';
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
    props: {
        /**
         * Show Slug
        */
        slug: {
            type: String
        }
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
            config: state => state.config.general,
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
        showSlug() {
            const { slug } = this;
            return slug || this.$route.query.showslug;
        },
        season() {
            return Number(this.$route.query.season);
        },
        episode() {
            if (this.$route.query.manual_search_type === 'season') {
                return;
            }
            return Number(this.$route.query.episode);
        },
        manualSearchType() {
            return this.$route.query.manual_search_type;
        }
    },
    methods: {
        ...mapActions({
            getShow: 'getShow'
        }),
        // TODO: Move this to show-results!
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

            return classes.join(' ');
        }
    },
    mounted() {
        const {
            show,
            showSlug,
            getShow,
            $store
        } = this;

        // Let's tell the store which show we currently want as current.
        $store.commit('currentShow', showSlug);

        // We need the show info, so let's get it.
        if (!show || !show.id.slug) {
            getShow({ showSlug, detailed: false });
        }
    }
};
</script>

<style scoped>
.show-history {
    margin-bottom: 10px;
}
</style>
