<template>
    <div class="show-selector form-inline hidden-print">
        <div class="select-show-group pull-left top-5 bottom-5">
            <select v-if="shows.length === 0" :class="selectClass" disabled>
                <option>Loading...</option>
            </select>
            <select v-else v-model="selectedShowSlug" :class="selectClass" @change="changeRoute($event.target.value);">
                <!-- placeHolder -->
                <option v-if="placeHolder" :value="placeHolder" disabled :selected="!selectedShowSlug" hidden>{{placeHolder}}</option>
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
import { mapActions, mapGetters, mapState } from 'vuex';
import { sortShows } from '../../utils/core';

export default {
    name: 'show-selector',
    props: {
        showSlug: String,
        followSelection: {
            type: Boolean,
            default: false
        },
        placeHolder: String,
        selectClass: {
            type: String,
            default: 'select-show form-control input-sm-custom'
        }
    },
    data() {
        return {
            $_selectedShow: '' // eslint-disable-line camelcase
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
        selectedShowSlug: {
            get() {
                const { placeHolder, showSlug, $_selectedShow } = this; // eslint-disable-line camelcase
                return $_selectedShow || showSlug || placeHolder; // eslint-disable-line camelcase
            },
            set(newSlug) {
                this.$_selectedShow = newSlug; // eslint-disable-line camelcase
            }
        },
        sortedLists() {
            const { layout, showsInLists } = this;
            const { sortArticle } = layout;

            const sortedShows = [...showsInLists];

            sortedShows.forEach(list => {
                list.shows = sortShows(list.shows, sortArticle);
            });

            return sortedShows;
        }
    },
    methods: {
        ...mapActions({
            setCurrentShow: 'setCurrentShow'
        }),
        async changeRoute(newShowSlug) {
            const { followSelection, shows, selectedShowSlug, setCurrentShow } = this;
            this.$emit('change', newShowSlug);

            if (!followSelection) {
                return;
            }

            const selectedShow = shows.find(show => show.id.slug === newShowSlug);
            if (!selectedShow || selectedShowSlug === newShowSlug) {
                return;
            }

            await setCurrentShow(newShowSlug);

            // To make it complete, make sure to switch route.
            this.$router.push({ query: { showslug: newShowSlug } });
        }
    },
    watch: {
        showSlug(newSlug) {
            this.selectedShowSlug = newSlug;
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
