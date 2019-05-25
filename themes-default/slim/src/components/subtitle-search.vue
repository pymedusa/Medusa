<template>
<!-- template for the subtitle-search component -->
<tr class='subtitle-search-wrapper'>
    <td colspan='9999' transition="expand">
        <span v-if="loading" class="loading-message">{{loadingMessage}} <state-switch :theme="config.themeName" state="loading"></state-switch></span>
        <div v-if="displayQuestion" class="search-question">
            <div class="question">
                <p>Do you want to manually pick subtitles or let us choose it for you?</p>
            </div>
            <div class="options">
                <button type="button" class="btn-medusa btn-info" @click="autoSearch">Auto</button>
                <button type="button" class="btn-medusa btn-success" @click="manualSearch">Manual</button>
            </div>
        </div>
        <!-- <h3>Subtitle results</h3> -->
            <vue-good-table v-if="subtitles.length"
                :columns="columns"
                :rows="subtitles"
                :search-options="{
                    enabled: false
                }"
                :sort-options="{
                    enabled: true,
                    initialSortBy: { field: 'score', type: 'desc' }
                }"
                styleClass="vgt-table condensed subtitle-table"
                >
                <template slot="table-column" slot-scope="props">
                    <span v-if="props.column.label == 'Download'">
                        <span>{{props.column.label}}</span>
                        <span class="btn-medusa btn-xs pull-right" @click="destroy">hide</span>
                    </span>
                    <span v-else>
                        {{props.column.label}}
                    </span>
                </template>
                <template slot="table-row" slot-scope="props">
                    <span v-if="props.column.field == 'provider'">
                        <img :src="`images/subtitles/${props.row.provider}.png`" width="16" height="16"/>
                        <span :title="props.row.provider">{{props.row.provider}}</span>
                    </span>
                    <span v-else-if="props.column.field == 'lang'">
                        <img :title="props.row.lang" :src="`images/subtitles/flags/${props.row.lang}.png`" width="16" height="11"/>
                    </span>
                    <span v-else-if="props.column.field == 'filename'">
                        <a :title="`Download ${props.row.hearing_impaired ? 'hearing impaired ' : ' '} subtitle: ${props.row.filename}`" @click="pickSubtitle(props.row.id)">
                            <img v-if="props.row.hearing_impaired" src="images/hearing_impaired.png" width="16" height="16"/>
                            <span class="subtitle-name">{{props.row.filename}}</span>
                            <img v-if="props.row.sub_score >= props.row.min_score" src="images/save.png" width="16" height="16"/>
                        </a>
                    </span>
                    <span v-else-if="props.column.field == 'download'">
                        <a :title="`Download ${props.row.hearing_impaired ? 'hearing impaired ' : ' '} subtitle: ${props.row.filename}`" @click="pickSubtitle(props.row.id)">
                            <img src="images/download.png" width="16" height="16"/>
                        </a>
                    </span>
                    <span v-else>
                        {{props.formattedRow[props.column.field]}}
                    </span>
                </template>
            </vue-good-table>
    </td>
</tr>
</template>
<script>

import { mapState } from 'vuex';
import { VueGoodTable } from 'vue-good-table';

export default {
    name: 'subtitle-search',
    components: {
        VueGoodTable
    },
    props: {
        show: {
            type: Object,
            required: true
        },
        season: {
            type: [String, Number],
            required: true
        },
        episode: {
            type: [String, Number],
            required: true
        }
    },
    data() {
        return {
            columns: [{
                label: 'Filename',
                field: 'filename'
            }, {
                label: 'Language',
                field: 'lang'
            }, {
                label: 'Provider',
                field: 'provider'
            }, {
                label: 'Score',
                field: 'score',
                type: 'number'
            }, {
                label: 'Sub Score',
                field: 'sub_score',
                type: 'number'
            }, {
                label: 'Missing Matches',
                field: rowObj => {
                    if (rowObj.missing_guess) {
                        return rowObj.missing_guess.join(', ');
                    }
                },
                type: 'array'
            }, {
                label: 'Download',
                field: 'download'
            }],
            subtitles: [],
            displayQuestion: false,
            loading: false,
            loadingMessage: ''
        };
    },
    computed: {
        ...mapState({
            config: state => state.config
        })
    },
    mounted() {
        this.displayQuestion = true;
    },
    methods: {
        autoSearch() {
            const { destroy, episode, season, show } = this;

            this.displayQuestion = false;
            const url = `home/searchEpisodeSubtitles?indexername=${show.indexer}&seriesid=${show.id[show.indexer]}&season=${season}&episode=${episode}`;
            this.loadingMessage = 'Searching for subtitles and downloading if available... ';
            this.loading = true;
            apiRoute(url) // eslint-disable-line no-undef
                .then(response => {
                    if (response.data.result !== 'failure') {
                        // Update the show, as we have new information (subtitles)
                        // Let's emit an event, telling the displayShow component, to update the show using the api/store.
                        this.$emit('update', {
                            reason: 'new subtitles found',
                            codes: response.data.subtitles,
                            languages: response.data.languages
                        });
                    }
                })
                .catch(error => {
                    console.log(`Error trying to search for subtitles. Error: ${error}`);
                })
                .finally(() => {
                    // Destroy this component.
                    this.loadingMessage = '';
                    this.loading = false;
                    destroy();
                });
        },
        manualSearch() {
            const { show, season, episode } = this;

            this.displayQuestion = false;
            this.loading = true;
            this.loadingMessage = 'Searching for subtitles... ';
            const url = `home/manualSearchSubtitles?indexername=${show.indexer}&seriesid=${show.id[show.indexer]}&season=${season}&episode=${episode}`;
            apiRoute(url) // eslint-disable-line no-undef
                .then(response => {
                    if (response.data.result === 'success') {
                        this.subtitles.push(...response.data.subtitles);
                    }
                }).catch(error => {
                    console.log(`Error trying to search for subtitles. Error: ${error}`);
                    this.destroy();
                }).finally(() => {
                    this.loading = false;
                });
        },
        destroy() {
            // Destroy the vue listeners, etc
            this.$destroy();
            // Remove the element from the DOM
            this.$el.parentNode.removeChild(this.$el);
        },
        pickSubtitle(subtitleId) {
            // Download and save this subtitle with the episode.
            const { show, season, episode } = this;

            this.displayQuestion = false;
            this.loadingMessage = 'downloading subtitle... ';
            this.loading = true;
            const url = `home/manualSearchSubtitles?indexername=${show.indexer}&seriesid=${show.id[show.indexer]}&season=${season}&episode=${episode}&picked_id=${subtitleId}`;
            apiRoute(url) // eslint-disable-line no-undef
                .then(response => {
                    if (response.data.result === 'success') {
                        // Update the show, as we have new information (subtitles)
                        // Let's emit an event, telling the displayShow component, to update the show using the api/store.
                        this.$emit('update', {
                            reason: 'new subtitles found',
                            codes: response.data.subtitles,
                            languages: response.data.languages
                        });
                    }
                })
                .catch(error => {
                    console.log(`Error trying to search for subtitles. Error: ${error}`);
                })
                .finally(() => {
                    // Destroy this component.
                    this.loadingMessage = '';
                    this.loading = false;
                    this.destroy();
                });
        }
    }
};
</script>
<style>
.v--modal-overlay .v--modal-box {
    overflow: inherit!important;
}
table.subtitle-table tr {
    background-color: rgb(190, 222, 237);
}
.subtitle-search-wrapper {
    display: table-row;
    column-span: all;
}
tr.subtitle-search-wrapper > td {
    padding: 0;
}
/* always present */
.expand-transition {
  transition: all .3s ease;
  height: 30px;
  padding: 10px;
  background-color: #eee;
  overflow: hidden;
}
/* .expand-enter defines the starting state for entering */
/* .expand-leave defines the ending state for leaving */
.expand-enter, .expand-leave {
  height: 0;
  padding: 0 10px;
  opacity: 0;
}
.search-question, .loading-message {
    background-color: rgb(51, 51, 51);
    color: rgb(255,255,255);
    padding: 10px;
    line-height: 55px;
}
span.subtitle-name {
    color: rgb(0, 0, 0);
}
</style>
