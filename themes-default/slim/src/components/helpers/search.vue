<template>
    <div class="search-wrapper">
        <img v-if="searchType === 'backlog'" class="epForcedSearch" :id="`${showSlug}x${episode.season}x${episode.episode}`"
             :name="`${showSlug}x${episode.season}x${episode.episode}`"
             :ref="`search-${episode.slug}`" :src="src" height="16"
             :alt="retryDownload(episode) ? 'retry' : 'search'"
             :title="retryDownload(episode) ? 'Retry Download' : 'Forced Seach'"
             @click="queueSearch(episode)"
             :disabled="disabled"
        >

        <app-link v-if="searchType === 'manual'" class="epManualSearch" :id="`${showSlug}x${episode.episode}`"
                  :name="`${showSlug}x${episode.season}x${episode.episode}`"
                  :href="`home/snatchSelection?showslug=${showSlug}&season=${episode.season}&episode=${episode.episode}`"
        >
            <img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search">
        </app-link>

        <!-- eslint-disable @sharkykh/vue-extra/component-not-registered -->
        <modal name="query-start-backlog-search" @before-open="beforeBacklogSearchModalClose" :height="'auto'" :width="'80%'">
            <transition name="modal">
                <div class="modal-mask">
                    <div class="modal-wrapper">
                        <div class="modal-content">
                            <div class="modal-header">
                                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                                <h4 class="modal-title">Start search?</h4>
                            </div>
                            <div class="modal-body">
                                <p>Some episodes have been changed to 'Wanted'. Do you want to trigger a backlog search for these {{backlogSearchEpisodes.length}} episode(s)</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn-medusa btn-danger" data-dismiss="modal" @click="$modal.hide('query-start-backlog-search')">No</button>
                                <button type="button" class="btn-medusa btn-success" data-dismiss="modal" @click="search(backlogSearchEpisodes, 'backlog'); $modal.hide('query-start-backlog-search')">Yes</button>
                            </div>
                        </div>
                    </div>
                </div>
            </transition>
        </modal>

        <modal name="query-mark-failed-and-search" @before-open="beforeFailedSearchModalClose" :height="'auto'" :width="'80%'">
            <transition name="modal">
                <div class="modal-mask">
                    <div class="modal-wrapper">
                        <div class="modal-content">
                            <div class="modal-header">
                                Mark episode as failed and search?
                            </div>

                            <div class="modal-body">
                                <p>Starting to search for the episode</p>
                                <p v-if="failedSearchEpisodes && failedSearchEpisodes.length === 1">Would you also like to mark episode {{failedSearchEpisodes[0].slug}} as "failed"? This will make sure the episode cannot be downloaded again</p>
                                <p v-else-if="failedSearchEpisodes">Would you also like to mark episodes {{failedSearchEpisodes.map(ep => ep.slug).join(', ')}} as "failed"? This will make sure the episode cannot be downloaded again</p>
                            </div>

                            <div class="modal-footer">
                                <button type="button" class="btn-medusa btn-danger" data-dismiss="modal" @click="search(failedSearchEpisodes, 'backlog'); $modal.hide('query-mark-failed-and-search')">No</button>
                                <button type="button" class="btn-medusa btn-success" data-dismiss="modal" @click="search(failedSearchEpisodes, 'failed'); $modal.hide('query-mark-failed-and-search')">Yes</button>
                                <button type="button" class="btn-medusa btn-danger" data-dismiss="modal" @click="$modal.hide('query-mark-failed-and-search')">Cancel</button>
                            </div>
                        </div>
                    </div>
                </div>
            </transition>
        </modal>
    </div>
</template>
<script>
import { mapState } from 'vuex';
import AppLink from './app-link.vue';

export default {
    name: 'search',
    components: {
        AppLink
    },
    props: {
        searchType: {
            type: String,
            default: 'forced',
            required: true,
            validator: value => ['backlog', 'manual'].includes(value)
        },
        showSlug: {
            type: String,
            required: true
        },
        episode: {
            type: Object,
            required: true
        }
    },
    data() {
        return {
            subtitleComponentInstance: null,
            failedSearchEpisodes: [],
            backlogSearchEpisodes: [],
            src: 'images/search16.png',
            disabled: false
        };
    },
    computed: {
        ...mapState({
            stateSearch: state => state.config.search,
            client: state => state.auth.client,
            queueitems: state => state.queue.queueitems
        })
    },
    methods: {
        retryDownload(episode) {
            const { stateSearch } = this;
            return (stateSearch.general.failedDownloads.enabled && ['Snatched', 'Snatched (Proper)', 'Snatched (Best)', 'Downloaded'].includes(episode.status));
        },
        search(episode, searchType) {
            const { showSlug } = this;
            let data = {};

            data = {
                showSlug,
                episodes: [episode.slug],
                options: {}
            };
            this.src = 'images/loading16-dark.gif';

            this.client.api.put(`search/${searchType}`, data) // eslint-disable-line no-undef
                .then(_ => {
                    console.info(`Queued search for show: ${showSlug} episode: ${episode.slug}`);
                    this.src = 'images/queued.png';
                    this.disabled = true;
                }).catch(error => {
                    console.error(String(error));
                    this.$refs[`search-${episode.slug}`].src = 'images/no16.png';
                }).finally(() => {
                    this.failedSearchEpisodes = [];
                    this.backlogSearchEpisodes = [];
                });
        },
        /**
         * Start a backlog search or failed search for the specific episode.
         * A failed search is started depending on the current episodes status.
         * @param {Object} episode - Episode object. If no episode object is passed, a backlog search is started.
         */
        queueSearch(episode) {
            const { $modal, search, retryDownload } = this;
            if (episode) {
                if (this.disabled === true) {
                    return;
                }

                if (retryDownload(episode)) {
                    $modal.show('query-mark-failed-and-search', { episode });
                } else {
                    search(episode, 'backlog');
                }
            }
        },
        /**
         * Vue-js-modal requires a method, to pass an event to.
         * The event then can be used to assign the value of the episode.
         * @param {Object} event - vue js modal event
         */
        beforeBacklogSearchModalClose(event) {
            this.backlogSearchEpisodes = event.params.episodes;
        },
        /**
         * Vue-js-modal requires a method, to pass an event to.
         * The event then can be used to assign the value of the episode.
         * @param {Object} event - vue js modal event
         */
        beforeFailedSearchModalClose(event) {
            this.failedSearchEpisodes = event.params.episodes;
        }
    },
    watch: {
        queueitems(queueitems) {
            const episode = queueitems.filter(
                q => q.name === 'BACKLOG' &&
                q.show &&
                q.show.id.slug === this.showSlug &&
                q.segment.find(s => s.slug === this.episode.slug)
            );

            if (episode.length === 0) {
                return;
            }

            const lastEp = episode.slice(-1)[0];
            if (lastEp.inProgress && lastEp.success === null) {
                // Search is in progress.
                console.info(`Search runnning for show: ${this.showSlug} and episode: ${this.episode.slug}`);
                this.src = 'images/loading16.gif';
                this.disabled = true;
            } else {
                // Search finished.
                console.log(`Search finished for ${this.episode.slug}`);
                this.src = 'images/yes16.png';
                this.disabled = false;
            }
        }
    }
};
</script>
<style scoped>
.mobile-select {
    width: 110px;
    font-size: x-small;
}

.search-wrapper {
    float: left;
}

.search-wrapper > img {
    cursor: pointer;
}
</style>
