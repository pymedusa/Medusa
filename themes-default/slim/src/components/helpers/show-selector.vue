<template>
    <div v-if="showForRoutes" class="show-selector form-inline hidden-print">
        <div class="select-show-group pull-left top-5 bottom-5">
            <select v-if="shows.length === 0" :class="selectClass" disabled>
                <option>Loading...</option>
            </select>
            <select v-else v-model="selectedShowSlug" :class="selectClass" @change="$emit('change', selectedShowSlug)">
                <!-- placeholder -->
                <option v-if="placeholder" :value="placeholder" disabled :selected="!selectedShowSlug" hidden>{{placeholder}}</option>
                <!-- If there are multiple show lists -->
                <template v-if="sortedLists && sortedLists.length > 1">
                    <optgroup v-for="list in sortedLists" :key="list.listTitle" :label="list.listTitle">
                        <option v-for="show in list.shows" :key="show.id.slug" :value="show.id.slug">{{show.title}}</option>
                    </optgroup>
                </template>
                <!-- If there is one list -->
                <template v-else>
                    <option v-for="show in sortedLists[0].shows" :key="show.id.slug" :value="show.id.slug">{{show.title}}</option>
                </template>
            </select>
        </div> <!-- end of select-show-group -->
    </div> <!-- end of container -->
</template>
<script>
import { mapGetters, mapState } from 'vuex';

export default {
    name: 'show-selector',
    props: {
        showSlug: String,
        followSelection: {
            type: Boolean,
            default: false
        },
        placeholder: String,
        selectClass: {
            type: String,
            default: 'select-show form-control input-sm-custom'
        }
    },
    data() {
        const selectedShowSlug = this.showSlug || this.placeholder;
        return {
            selectedShowSlug
        };
    },
    computed: {
        ...mapState({
            layout: state => state.config.layout,
            shows: state => state.shows.shows
        }),
        ...mapGetters({
            showsInLists: 'showsInLists'
        }),
        sortedLists() {
            const { layout, showsInLists } = this;
            const { sortArticle } = layout;

            const sortedShows = [...showsInLists];

            const sortKey = title => (sortArticle ? title.replace(/^((?:the|a|an)\s)/i, '') : title).toLowerCase();
            const sortFn = (showA, showB) => {
                const titleA = sortKey(showA.title);
                const titleB = sortKey(showB.title);
                if (titleA < titleB) {
                    return -1;
                }
                if (titleA > titleB) {
                    return 1;
                }
                return 0;
            };

            sortedShows.forEach(list => {
                list.shows.sort(sortFn);
            });

            return sortedShows;
        },
        showForRoutes() {
            const { $route } = this;
            return ['show', 'editShow'].includes($route.name);
        }
    },
    watch: {
        showSlug(newSlug) {
            this.selectedShowSlug = newSlug;
        },
        async selectedShowSlug(newSlug) {
            if (!this.followSelection) {
                return;
            }

            const { $store, shows } = this;
            const selectedShow = shows.find(show => show.id.slug === newSlug);
            if (!selectedShow) {
                return;
            }
            const indexerName = selectedShow.indexer;
            const seriesId = selectedShow.id[indexerName];

            // Get detailed show information. We need to wait for this, in order for the watch('show.id.slug') in displayShow
            // to have the detailed show information.
            await $store.dispatch('getShow', { id: seriesId, indexer: indexerName, detailed: true });

            // Make sure the correct show, has been set as current show.
            console.debug(`Setting current show to ${selectedShow.title}`);
            $store.commit('currentShow', {
                indexer: indexerName,
                id: seriesId
            });

            // To make it complete, make sure to switch route.
            this.$router.push({ query: { indexername: indexerName, seriesid: String(seriesId) } });
        }
    }
};
</script>
<style>
select.select-show {
    display: inline-block;
    height: 25px;
    padding: 1px;
    min-width: 200px;
}

.show-selector {
    height: 31px;
    display: table-cell;
    left: 20px;
    margin-bottom: 5px;
}

@media (max-width: 767px) and (min-width: 341px) {
    .select-show-group,
    .select-show {
        width: 100%;
    }
}

@media (max-width: 340px) {
    .select-show-group {
        width: 100%;
    }
}

@media (max-width: 767px) {
    .show-selector {
        float: left;
        width: 100%;
    }

    .select-show {
        width: 100%;
    }
}
</style>
