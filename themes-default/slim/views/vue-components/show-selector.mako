<style>
select#select-show {
    display: inline-block;
    height: 25px;
    padding: 1px;
}

#showSelector {
    height: 31px;
    display: table-cell;
    left: 20px;
    margin-bottom: 5px;
}

@media (max-width: 767px) and (min-width: 341px) {
    .select-show-group {
        width: 100%;
    }

    .show-selector {
        width: 100%;
    }

    .showSelector {
        width: 100%;
    }
}

@media (max-width: 340px) {
    .select-show-group {
        width: 100%;
    }

    .container-navShow {
        margin-left: 265px;
    }
}

@media (max-width: 767px) {
    #showSelector {
        float: left;
        width: 100%;
    }

    .select-show {
        width: 100%;
    }
}
</style>
<script type="text/x-template" id="show-selector-template">
    <div id="showSelector" class="hidden-print">
        <div class="form-inline">
            <div>
                <div class="select-show-group pull-left top-5 bottom-5">
                    <select v-model="selectedShowSlug" @change="jumpToShow" id="select-show" class="form-control input-sm-custom show-selector">
                        <template v-if="whichList === -1">
                            <optgroup v-for="curShowList in showLists" :label="curShowList.type">
                                <option v-for="curShow in curShowList.shows" :value="curShow.id.slug">
                                    {{curShow.title}}
                                </option>
                            </optgroup>
                        </template>
                        <template v-else>
                            <option v-for="curShow in showLists[whichList].shows" :value="curShow.id.slug">
                                {{curShow.title}}
                            </option>
                        </template>
                    </select>
                </div> <!-- end of select-show-group -->
            </div>
        </div>
    </div> <!-- end of container -->
</script>
<script>
Vue.component('show-selector', {
    template: '#show-selector-template',
    props: {
        currentShowSlug: String
    },
    data() {
        return {
            selectedShowSlug: this.currentShowSlug
        };
    },
    computed: Object.assign(store.mapState(['config', 'shows']), {
        showLists() {
            const { config, shows } = this;
            const { sortArticle } = config;
            const lists = [
                { type: 'Shows', shows: [] },
                { type: 'Anime', shows: [] }
            ];

            shows.forEach(show => {
                const type = show.config.anime === true ? 1 : 0;
                lists[type].shows.push(show);
            });

            const sortKey = (title) => (sortArticle ? title : title.replace(/^((?:The|A|An)\s)/i, '')).toLowerCase();
            lists.forEach(list => {
                list.shows.sort((showA, showB) => {
                    const titleA = sortKey(showA.title);
                    const titleB = sortKey(showB.title);
                    if (titleA < titleB) return -1;
                    if (titleA > titleB) return 1;
                    return 0;
                });
            });
            return lists;
        },
        whichList() {
            const { showLists } = this;
            const shows = showLists[0].shows.length !== 0;
            const anime = showLists[1].shows.length !== 0;
            if (shows && anime) return -1;
            if (anime) return 1;
            return 0;
        }
    }),
    methods: {
        jumpToShow() {
            const { selectedShowSlug, shows } = this;
            const selectedShow = shows.find(show => show.id.slug === selectedShowSlug);
            if (!selectedShow) return;
            const indexerName = selectedShow.indexer;
            const showId = selectedShow.id[indexerName];
            const base = document.getElementsByTagName('base')[0].getAttribute('href');
            const path = 'home/displayShow?indexername=' + indexerName + '&seriesid=' + showId;
            window.location.href = base + path;
        }
    }
});
</script>