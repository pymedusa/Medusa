<template>
    <div class="show-selector form-inline hidden-print">
        <div class="select-show-group pull-left top-5 bottom-5">
            <select v-if="shows.length === 0" :class="selectClass" disabled>
                <option>Loading...</option>
            </select>
            <select v-else v-model="selectedShowSlug" :class="selectClass" @change="$emit('change', selectedShowSlug)">
                <option v-if="placeholder" :value="placeholder" disabled :selected="!selectedShowSlug" hidden>{{placeholder}}</option>
                <template v-if="whichList === -1">
                    <optgroup v-for="curShowList in showLists" :key="curShowList.type" :label="curShowList.type">
                        <option v-for="show in curShowList.shows" :key="show.id.slug" :value="show.id.slug">{{show.title}}</option>
                    </optgroup>
                </template>
                <template v-else>
                    <option v-for="show in showLists[whichList].shows" :key="show.id.slug" :value="show.id.slug">{{show.title}}</option>
                </template>
            </select>
        </div> <!-- end of select-show-group -->
    </div> <!-- end of container -->
</template>
<script>
import { mapState } from 'vuex';

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
            selectedShowSlug,
            lock: false
        };
    },
    computed: {
        ...mapState({
            layout: state => state.layout,
            shows: state => state.shows.shows
        }),
        showLists() {
            const { layout, shows } = this;
            const { animeSplitHome, sortArticle } = layout;
            const lists = [
                { type: 'Shows', shows: [] },
                { type: 'Anime', shows: [] }
            ];

            // We're still loading
            if (shows.length === 0) {
                return;
            }

            shows.forEach(show => {
                const type = Number(animeSplitHome && show.config.anime);
                lists[type].shows.push(show);
            });

            const sortKey = title => (sortArticle ? title : title.replace(/^((?:The|A|An)\s)/i, '')).toLowerCase();
            lists.forEach(list => {
                list.shows.sort((showA, showB) => {
                    const titleA = sortKey(showA.title);
                    const titleB = sortKey(showB.title);
                    if (titleA < titleB) {
                        return -1;
                    }
                    if (titleA > titleB) {
                        return 1;
                    }
                    return 0;
                });
            });
            return lists;
        },
        whichList() {
            const { showLists } = this;
            const shows = showLists[0].shows.length !== 0;
            const anime = showLists[1].shows.length !== 0;
            if (shows && anime) {
                return -1;
            }
            if (anime) {
                return 1;
            }
            return 0;
        }
    },
    watch: {
        showSlug(newSlug) {
            this.lock = true;
            this.selectedShowSlug = newSlug;
        },
        selectedShowSlug(newSlug) {
            if (this.lock) {
                this.lock = false;
                return;
            }

            if (!this.followSelection) {
                return;
            }

            const { shows } = this;
            const selectedShow = shows.find(show => show.id.slug === newSlug);
            if (!selectedShow) {
                return;
            }
            const indexerName = selectedShow.indexer;
            const showId = selectedShow.id[indexerName];
            const base = document.querySelector('base').getAttribute('href');
            window.location.href = `${base}home/displayShow?indexername=${indexerName}&seriesid=${showId}`;
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
