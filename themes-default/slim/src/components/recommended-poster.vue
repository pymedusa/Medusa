<template>
    <div class="poster-wrapper">
        <div class="recommended-image">
            <app-link :href="show.imageHref">
                <asset :default-src="show.imageSrc" lazy type="posterThumb" cls="show-image" :link="false" height="273px" :img-width="186" />
            </app-link>

            <div v-if="show.genres.length > 0" class="tag-container">
                <ul class="genre-tags">
                    <li v-for="genre in show.genres" :key="genre">{{genre}}</li>
                </ul>
            </div>

            <transition name="plot">
                <div v-if="displayPlot && show.plot" class="plot-overlay">
                    <span>{{show.plot}}</span>
                </div>
            </transition>
        </div>

        <div class="check-overlay" />

        <div class="show-title">
            <span :title="show.title">{{show.title}}</span>
            <div v-if="show.plot" class="toggle-plot" @click="displayPlot = !displayPlot">
                <span v-if="displayPlot">hide plot</span>
                <span v-else>show plot</span>
            </div>
        </div>

        <div class="row">
            <div name="left" class="col-md-7 col-xs-12">
                <div class="show-rating">
                    <p>{{show.rating.toFixed(1)}} <img src="images/heart.png">
                        <template v-if="show.isAnime" id="linkAnime">
                            <app-link class="recommended-show-url" :href="`https://anidb.net/a${show.externals.aid}`">
                                <img src="images/anidb_inline_refl.png" class="recommended-show-link-inline" alt="">
                            </app-link>
                        </template>
                        <template v-if="show.recommender === 'Trakt Popular'" id="linkAnime">
                            <a class="recommended-show-url" :href="`https://trakt.tv/shows/${show.seriesId}`">
                                <img src="images/trakt.png" class="recommended-show-link-inline" alt="">
                            </a>
                        </template>
                    </p>
                </div>

                <div class="show-votes">
                    <i>x {{show.votes}}</i>
                </div>

            </div>

            <div name="right" class="col-md-5 col-xs-12">
                <div class="recommendedShowTitleIcons">
                    <button v-if="traktConfig.removedFromMedusa && traktConfig.removedFromMedusa.includes(show.mappedSeriesId)" class="btn-medusa btn-xs">
                        <app-link :href="`home/displayShow?indexername=${show.mappedIndexerName}&seriesid=${show.mappedSeriesId}`">Watched</app-link>
                    </button>
                    <button :disabled="show.trakt.blacklisted" v-if="show.source === externals.TRAKT" :data-indexer-id="show.mappedSeriesId" class="btn-medusa btn-xs" @click="blacklistTrakt(show)">Blacklist</button>
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-md-12 addshowoptions">
                <template v-if="show.showInLibrary">
                    <button v-if="show.showInLibrary" class="btn-medusa btn-xs">
                        <div v-if="addingShow.started && addingShow.progress !== 100" class="add-show-progress" style="">
                            <span>Adding Show...</span>
                            <div class="steps">
                                <ul>
                                    <li v-for="step in addingShow.steps" :key="step">
                                        <span>{{step}}</span>
                                    </li>
                                </ul>
                            </div>
                            <div class="bar" :style="`width: ${addingShow.progress}%`" />
                        </div>
                        <app-link v-else :href="`home/displayShow?showslug=${show.showInLibrary}`">Open in library</app-link>
                    </button>
                </template>
                <template v-else>
                    <select :ref="`${show.source}-${show.seriesId}`" v-model="selectedAddShowOption" name="addshow" class="rec-show-select">
                        <option v-for="option in addShowOptions(show)" :value="option.value" :key="option.value">{{option.text}}</option>
                    </select>
                    <button :disabled="show.trakt.blacklisted" class="btn-medusa btn-xs rec-show-button" @click="addShow(show)">
                        Search/Add
                    </button>
                </template>
            </div>
        </div>
    </div>
</template>

<script>
import { mapState } from 'vuex';
import {
    Asset,
    AppLink
} from './helpers';

export default {
    name: 'recommended-poster',
    components: {
        Asset,
        AppLink
    },
    props: {
        show: {
            type: Object,
            required: true
        }
    },
    data() {
        return {
            displayPlot: false,
            selectedAddShowOption: 'search',
            addingShow: {
                identifier: null,
                progress: 0,
                started: false,
                steps: []
            }
        };
    },
    computed: {
        ...mapState({
            traktConfig: state => state.recommended.trakt,
            externals: state => state.recommended.externals,
            queueitems: state => state.shows.queueitems,
            client: state => state.auth.client
        })
    },
    methods: {
        addShow(show) {
            const { selectedAddShowOption } = this;
            if (selectedAddShowOption === 'search') {
                // Route to the add-new-show.vue component, with the show's title.
                this.$router.push({
                    name: 'addNewShow',
                    params: {
                        providedInfo: {
                            showName: show.title
                        }
                    }
                });
                return;
            }

            let showId = null;
            let showSlug = '';
            if (Object.keys(show.externals).length !== 0 && show.externals[selectedAddShowOption + '_id']) {
                showId = { [selectedAddShowOption]: show.externals[selectedAddShowOption + '_id'] };
                showSlug = show.externals[selectedAddShowOption + '_id'];
            } else if (show.source === this.externals.IMDB && selectedAddShowOption === 'imdb') {
                showId = { [selectedAddShowOption]: show.seriesId };
                showSlug = show.seriesId;
            }

            if (this.addShowById(showId)) {
                show.showInLibrary = `${selectedAddShowOption}${showSlug}`;
            }
        },
        /**
         * Add by show id.
         * @param {number} showId - Show id.
         */
        async addShowById(showId) {
            const { enableShowOptions, selectedShowOptions } = this;

            const options = {};

            if (enableShowOptions) {
                options.options = selectedShowOptions;
            }

            try {
                const response = await this.client.api.post('series', { id: showId, options });
                if (response && response.data && response.data.identifier) {
                    this.addingShow.identifier = response.data.identifier;
                    this.addingShow.started = true;
                }

                this.$snotify.success(
                    'Adding new show to library',
                    'In progress',
                    { timeout: 20000 }
                );
                return true;
            } catch (error) {
                this.$snotify.error(
                    'Error while trying to add new show',
                    'Error'
                );
            }
            return false;
        },
        blacklistTrakt(show) {
            show.trakt.blacklisted = true;
            this.client.apiRoute(`addShows/addShowToBlacklist?seriesid=${show.externals.tvdb_id}`);
        },
        addShowOptions(show) {
            const { externals } = show;
            if (show.isAnime) {
                return [{ text: 'Tvdb', value: 'tvdb_id' }];
            }

            const options = [];
            // Add through the add-new-show.vue component
            options.push({ text: 'search show', value: 'search' });

            for (const external in externals) {
                if (['tvdb_id', 'tmdb_id', 'tvmaze_id', 'imdb_id'].includes(external)) {
                    const externalName = external.split('_')[0];
                    options.push({ text: externalName, value: externalName });
                }
            }

            if (show.source === this.externals.IMDB) {
                options.push({ text: 'imdb', value: 'imdb' });
            }

            return options;
        }
    },
    watch: {
        queueitems(queueItem) {
            const { addingShow } = this;
            if (!addingShow.started || !addingShow.identifier) {
                return;
            }
            const foundItem = queueItem.find(item => item.identifier === addingShow.identifier);
            if (foundItem) {
                this.addingShow.steps = foundItem.step;
                this.addingShow.progress = 100 / 6 * this.addingShow.steps.length;
                if (foundItem.success) {
                    this.addingShow.progress = 100;
                }
            }
        }
    }
};
</script>

<style scoped>
.tag-container {
    opacity: 0;
    position: absolute;
    top: 3px;
    right: 0;
    -webkit-transition: opacity 0.2s ease-in-out;
    -moz-transition: opacity 0.2s ease-in-out;
    -ms-transition: opacity 0.2s ease-in-out;
    -o-transition: opacity 0.2s ease-in-out;
    transition: opacity 0.2s ease-in-out;
}

.recommended-image:hover {
    opacity: 0.9;
}

.recommended-image:hover .tag-container {
    display: block;
    opacity: 0.9;
}

ul.genre-tags {
    margin-right: 2px;
}

ul.genre-tags > li {
    margin-right: 1px;
    margin-bottom: 2px;
    padding: 2px 4px;
    background: rgb(21, 82, 143);
    border-radius: 1px;
    border: 1px solid rgb(17, 17, 17);
    color: rgb(255, 255, 255);
    font: 14px/18px "Open Sans", "Helvetica Neue", Helvetica, Arial, Geneva, sans-serif;
    text-shadow: 0 1px rgb(0 0 0 / 80%);
    float: right;
    list-style: none;
}

select.max-width {
    max-width: 430px;
}

.plot-overlay {
    opacity: 0.9;
    width: 100%;
    height: 100%;
    position: absolute;
    bottom: 0;
    overflow-y: auto;
    background-color: rgb(51, 51, 51);
    scrollbar-color: rgb(65, 0, 181) darkgrey;
    scrollbar-width: thin;
}

.plot-overlay > span {
    padding: 2px 5px;
    height: 100%;
    display: block;
    font-size: 11px;
    color: white;
}

.plot-overlay::-webkit-scrollbar {
    width: 6px; /* width of the entire scrollbar */
}

.plot-overlay::-webkit-scrollbar-track {
    background: darkgrey; /* color of the tracking area */
}

.plot-overlay::-webkit-scrollbar-thumb {
    background-color: rgb(65, 0, 181); /* color of the scroll thumb */
    border-radius: 1px; /* roundness of the scroll thumb */
    border: 0 solid rgb(5, 36, 249); /* creates padding around scroll thumb */
}

.recommended-image {
    position: relative;
    overflow: hidden;
}

.recommended-image >>> .show-image {
    height: 100%;
}

.show-image {
    height: 100%;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
}

.toggle-plot {
    position: absolute;
    right: 0;
    top: 0;
    z-index: 1;
    text-decoration: underline;
    cursor: pointer;
    padding: 0 2px;
}

.plot-enter-active,
.plot-leave-active {
    -moz-transition-duration: 0.3s;
    -webkit-transition-duration: 0.3s;
    -o-transition-duration: 0.3s;
    transition-duration: 0.3s;
    -moz-transition-timing-function: ease-in;
    -webkit-transition-timing-function: ease-in;
    -o-transition-timing-function: ease-in;
    transition-timing-function: ease-in;
}

.plot-enter-to,
.plot-leave {
    bottom: 0;
}

.plot-enter,
.plot-leave-to {
    bottom: -100%;
}

.add-show-progress {
    width: 95px;
    height: 21px;
    position: relative;
}

.add-show-progress > .bar {
    background-color: darkgrey;
    height: 100%;
    width: 0;
    position: absolute;
    top: 0;
    opacity: 0.4;
}

.add-show-progress > .steps {
    display: none;
    position: absolute;
    background-color: rgb(95, 95, 95);
    font-size: 14px;
    border: 1px solid rgb(125, 125, 125);
    z-index: 1;
    width: auto;
    white-space: nowrap;
}

.add-show-progress:hover > .steps {
    display: block;
}

.add-show-progress > .steps ul {
    padding: 2px 5px;
}

.add-show-progress > .steps li {
    list-style-type: none;
    text-align: left;
}
</style>
