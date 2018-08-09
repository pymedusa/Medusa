<template>
    <span v-if="shows.length === 0">Loading...</span>
    <div v-else class="show-selector form-inline hidden-print">
        <div class="select-show-group pull-left top-5 bottom-5">
            <select v-model="selectedShowSlug" class="select-show form-control input-sm-custom">
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
import Vuex from 'vuex';

module.exports = {
    name: 'show-selector',
    props: {
        showSlug: String
    },
    data() {
        return {
            selectedShowSlug: this.showSlug,
            lock: false
        };
    },
    computed: Object.assign(Vuex.mapState(['config', 'shows']), {
        showLists() {
            const { config, shows } = this;
            const { animeSplitHome, sortArticle } = config;
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
    }),
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
            const { shows } = this;
            const selectedShow = shows.find(show => show.id.slug === newSlug);
            if (!selectedShow) {
                return;
            }
            const indexerName = selectedShow.indexer;
            const showId = selectedShow.id[indexerName];
            const base = document.getElementsByTagName('base')[0].getAttribute('href');
            const path = 'home/displayShow?indexername=' + indexerName + '&seriesid=' + showId;
            window.location.href = base + path;
        }
    }
};
</script>
<style>
select.select-show {
    display: inline-block;
    height: 25px;
    padding: 1px;
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
