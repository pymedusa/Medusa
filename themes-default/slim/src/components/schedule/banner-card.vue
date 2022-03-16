<template>
    <div class="card-wrapper">
        <div v-if="layout === 'banner'" class="card">
            <div class="episode-card-inner">
                <div class="row">
                    <div class="col-lg-12">
                        <app-link :href="`home/displayShow?showslug=${episode.showSlug}`">
                            <asset default-src="images/banner.png" :show-slug="episode.showSlug" type="banner" cls="bannerThumb" :link="false" />
                        </app-link>
                    </div>
                </div>
                <div class="row">
                    <div class="col-lg-12">
                        <div class="card-bottom">
                            <div class="row">
                                <div class="col-lg-8">
                                    <div class="row">
                                        <div class="col-lg-12 tvshowTitle">
                                            <app-link :href="`home/displayShow?showslug=${episode.showSlug}`">
                                                {{episode.showName}}
                                                <span v-if="episode.paused" class="pause"> [paused]</span>
                                            </app-link>
                                        </div>
                                    </div>

                                    <div class="row">
                                        <div class="col-lg-12">
                                            <span class="title">Next Episode:</span>
                                            <span>{{episode.episodeSlug}}</span>
                                            <span v-if="episode.epName"> - {{episode.epName}}</span>
                                        </div>
                                    </div>

                                    <div class="row">
                                        <div class="col-lg-12">
                                            <span class="title">Airs: </span>
                                            <span class="airdate">{{fuzzyParseDateTime(episode.localAirTime)}}</span>
                                            <span v-if="episode.network"> on {{episode.network}}</span>
                                        </div>
                                    </div>

                                    <div class="row">
                                        <div class="col-lg-12">
                                            <span class="title">Quality:</span>
                                            <quality-pill :quality="episode.quality" show-title />
                                        </div>
                                    </div>

                                    <div class="row">
                                        <div class="col-lg-12">
                                            <span class="title" :class="{'summary-trigger-none': !episode.epPlot}" style="vertical-align:middle;">Plot:</span>
                                            <img :class="[episode.epPlot ? 'summary-trigger': 'summary-trigger-none']"
                                                 src="images/plus.png" height="16" width="16" alt=""
                                                 title="Toggle Summary" @click="togglePlot(`${episode.showSlug}${episode.episodeSlug}`)">
                                            <div :ref="`${episode.showSlug}${episode.episodeSlug}`" v-show="episode.epPlot" class="summary">{{episode.epPlot}}</div>
                                        </div>
                                    </div>
                                </div>

                                <div class="col-lg-4">
                                    <div class="tvshowTitleIcons">
                                        <app-link v-if="episode.externals.imdb_id" :href="`http://www.imdb.com/title/${episode.externals.imdb_id}`" :title="`http://www.imdb.com/title/${episode.externals.imdb_id}`">
                                            <img alt="[imdb]" height="16" width="16" src="images/imdb16.png">
                                        </app-link>

                                        <app-link :href="`${getIndexer(episode.indexer).showUrl}${episode.indexerId}`"
                                                  :title="`${getIndexer(episode.indexer).showUrl}${episode.indexerId}`">
                                            <img :alt="`${getIndexer(episode.indexer).name}`" height="16" width="16" :src="`images/${getIndexer(episode.indexer).icon}`">
                                        </app-link>

                                        <search searchType="backlog" :showSlug="episode.showSlug" :episode="{
                                            episode: episode.episode, season: episode.season, slug: episode.episodeSlug
                                        }" />
                                        <search searchType="manual" :showSlug="episode.showSlug" :episode="{
                                            episode: episode.episode, season: episode.season, slug: episode.episodeSlug
                                        }" />
                                    </div>
                                </div>
                            </div>
                        </div> <!-- End of card bottom -->
                    </div>
                </div>
            </div>
        </div>

        <!-- Poster layout -->
        <div v-else class="card">
            <div class="episode-card-inner poster">
                <div class="poster-left">
                    <app-link :href="`home/displayShow?showslug=${episode.showSlug}`">
                        <asset default-src="images/banner.png" :show-slug="episode.showSlug" type="posterThumb" cls="posterThumb" :link="false" />
                    </app-link>
                </div>
                <div class="poster-right">
                    <div class="row">
                        <div class="col-lg-8 col-sm-12">
                            <div class="row">
                                <div class="col-lg-12 tvshowTitle">
                                    <app-link :href="`home/displayShow?showslug=${episode.showSlug}`">
                                        {{episode.showName}}<span v-if="episode.paused" class="pause"> [paused]</span>
                                    </app-link>
                                </div>
                            </div>

                            <div class="row">
                                <div class="col-lg-12">
                                    <span class="title">Next Episode:</span>
                                    <span>{{episode.episodeSlug}}</span><span v-if="episode.epName"> - {{episode.epName}}</span>
                                </div>
                            </div>

                            <div class="row">
                                <div class="col-lg-12">
                                    <span class="title">Airs: </span><span class="airdate">{{fuzzyParseDateTime(episode.localAirTime)}}</span>
                                    <span v-if="episode.network"> on {{episode.network}}</span>
                                </div>
                            </div>

                            <div class="row">
                                <div class="col-lg-12">
                                    <span class="title">Quality:</span>
                                    <quality-pill :quality="episode.quality" show-title />
                                </div>
                            </div>

                            <div class="row">
                                <div class="col-lg-12">
                                    <span class="title" :class="{'summary-trigger-none': !episode.epPlot}" style="vertical-align:middle;">Plot:</span>
                                    <img :class="[episode.epPlot ? 'summary-trigger': 'summary-trigger-none']"
                                         src="images/plus.png" height="16" width="16" alt=""
                                         title="Toggle Summary" @click="togglePlot(`${episode.showSlug}${episode.episodeSlug}`)">
                                    <div :ref="`${episode.showSlug}${episode.episodeSlug}`" v-show="episode.epPlot" class="summary">{{episode.epPlot}}</div>
                                </div>
                            </div>

                        </div>
                        <div class="col-lg-4 col-sm-12">
                            <span class="tvshowTitleIcons">
                                <app-link v-if="episode.externals.imdb_id" :href="`http://www.imdb.com/title/${episode.externals.imdb_id}`" :title="`http://www.imdb.com/title/${episode.externals.imdb_id}`">
                                    <img alt="[imdb]" height="16" width="16" src="images/imdb16.png">
                                </app-link>

                                <app-link :href="`${getIndexer(episode.indexer).showUrl}${episode.indexerId}`"
                                          :title="`${getIndexer(episode.indexer).showUrl}${episode.indexerId}`">
                                    <img :alt="`${getIndexer(episode.indexer).name}`" height="16" width="16" :src="`images/${getIndexer(episode.indexer).icon}`">
                                </app-link>

                                <search searchType="backlog" :showSlug="episode.showSlug" :episode="{
                                    episode: episode.episode, season: episode.season, slug: episode.episodeSlug
                                }" />
                                <search searchType="manual" :showSlug="episode.showSlug" :episode="{
                                    episode: episode.episode, season: episode.season, slug: episode.episodeSlug
                                }" />
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

    </div>
</template>
<script>
import { mapGetters } from 'vuex';
import { AppLink, Asset, Search, QualityPill } from '../helpers';

export default {
    name: 'banner-card',
    props: {
        episode: {
            type: Object
        },
        layout: {
            type: String,
            default: 'banner',
            allowed: value => ['banner', 'poster'].includes(value)
        }
    },
    components: {
        AppLink,
        Asset,
        Search,
        QualityPill
    },
    computed: {
        ...mapGetters([
            'getIndexer',
            'fuzzyParseDateTime'
        ])
    },
    methods: {
        togglePlot(id) {
            if (this.$refs[id].style.display === 'none') {
                this.$refs[id].style.display = 'block';
            } else {
                this.$refs[id].style.display = 'none';
            }
        }
    }
};
</script>

<style scoped>
.card {
    width: auto;
    border: 1px solid rgb(204, 204, 204);
    margin-bottom: 10px;
    padding: 10px;
}

.episode-card-inner {
    display: block;
    border: 1px solid rgb(204, 204, 204);
    margin: auto;
    padding: 0;
    text-align: left;
    max-width: 750px;
    border-radius: 5px;
    background: rgb(255, 255, 255);
    cursor: default;
    overflow: hidden;
    color: rgb(0, 0, 0);
}

.episode-card-inner.poster {
    display: flex;
}

.card-bottom {
    padding: 10px;
}

.summary {
    margin-left: 5px;
    font-style: italic;
    display: none;
}

.summary-trigger {
    cursor: pointer;
    vertical-align: middle;
}

.summary-trigger-none {
    opacity: 0.4;
    vertical-align: middle;
}

.poster-left,
.poster-right {
    float: left;
}

.poster-right {
    flex: auto;
    margin: 10px;
}

</style>
