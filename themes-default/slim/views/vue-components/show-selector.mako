<script type="text/x-template" id="show-selector-template">
    <div class="show-selector form-inline hidden-print">
        <div class="select-show-group pull-left top-5 bottom-5">
            <select v-model="selectedShowSlug" class="select-show form-control input-sm-custom">
                <template v-if="whichList === -1">
                    <optgroup v-for="curShowList in showLists" :label="curShowList.type">
                        <option v-for="show in curShowList.shows" :value="show.id.slug">{{show.title}}</option>
                    </optgroup>
                </template>
                <template v-else>
                    <option v-for="show in showLists[whichList].shows" :value="show.id.slug">{{show.title}}</option>
                </template>
            </select>
        </div> <!-- end of select-show-group -->
    </div> <!-- end of container -->
</script>
<script>
Vue.component('show-selector', {
    template: '#show-selector-template',
    props: {
        showSlug: String
    },
    data() {
        return {
            selectedShowSlug: this.showSlug
        };
    },
    computed: Object.assign(store.mapState(['config', 'shows']), {
        showLists() {
            const { config, shows } = this;
            const { animeSplitHome, sortArticle } = config;
            const lists = [
                { type: 'Shows', shows: [] },
                { type: 'Anime', shows: [] }
            ];

            shows.forEach(show => {
                const type = Number(animeSplitHome && show.config.anime);
                lists[type].shows.push(show);
            });

            const sortKey = title => (sortArticle ? title : title.replace(/^((?:The|A|An)\s)/i, '')).toLowerCase();
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
        selectedShowSlug(newSlug) {
            const { shows } = this;
            const selectedShow = shows.find(show => show.id.slug === newSlug);
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

