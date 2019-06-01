<template>
<!-- template for the subtitle-search component -->
<tr class="subtitle-search-wrapper">
    <td colspan="9999">
        <span v-if="loading" class="loading-message">{{loadingMessage}} <state-switch :theme="config.themeName" state="loading"/></span>
        <div v-if="displayQuestion" class="search-question">
            <div class="question">
                <p>Do you want to manually pick subtitles or let us choose it for you?</p>
            </div>
            <div class="options">
                <button type="button" class="btn-medusa btn-info" @click="autoSearch">Auto</button>
                <button type="button" class="btn-medusa btn-success" @click="manualSearch">Manual</button>
            </div>
        </div>

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
            <template v-slot:table-column="props">
                <span v-if="props.column.label === 'Download'">
                    <span>{{props.column.label}}</span>
                    <span class="btn-medusa btn-xs pull-right" @click="close">hide</span>
                </span>
                <span v-else>
                    {{props.column.label}}
                </span>
            </template>
            <template v-slot:table-row="props">
                <span v-if="props.column.field === 'provider'">
                    <img :src="`images/subtitles/${props.row.provider}.png`" width="16" height="16"/>
                    <span :title="props.row.provider">{{props.row.provider}}</span>
                </span>
                <span v-else-if="props.column.field === 'lang'">
                    <img :title="props.row.lang" :src="`images/subtitles/flags/${props.row.lang}.png`" width="16" height="11"/>
                </span>
                <span v-else-if="props.column.field === 'filename'">
                    <a :title="`Download ${props.row.hearing_impaired ? 'hearing impaired ' : ' '} subtitle: ${props.row.filename}`" @click="pickSubtitle(props.row.id)">
                        <img v-if="props.row.hearing_impaired" src="images/hearing_impaired.png" width="16" height="16"/>
                        <span class="subtitle-name">{{props.row.filename}}</span>
                        <img v-if="props.row.sub_score >= props.row.min_score" src="images/save.png" width="16" height="16"/>
                    </a>
                </span>
                <span v-else-if="props.column.field === 'download'">
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
import { apiRoute } from '../api';
import { StateSwitch } from './helpers';

export default {
    name: 'subtitle-search',
    components: {
        StateSwitch,
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
                field: 'download',
                sortable: false
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
        }),
        subtitleParams() {
            const { episode, show, season } = this;
            const params = {
                indexername: show.indexer,
                seriesid: show.id[show.indexer],
                season,
                episode
            }

            return params;
        },
    },
    mounted() {
        this.displayQuestion = true;
    },
    methods: {
        autoSearch() {
            const { episode, season } = this;

            this.displayQuestion = false;
            this.loadingMessage = 'Searching for subtitles and downloading if available... ';
            this.loading = true;
            apiRoute('home/searchEpisodeSubtitles', { params: subtitleParams }) // eslint-disable-line no-undef
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
                    // Cleanup
                    this.loadingMessage = '';
                    this.loading = false;
                    this.close();
                });
        },
        manualSearch() {
            const { season, episode, getSubtitleParams } = this;

            this.displayQuestion = false;
            this.loading = true;
            this.loadingMessage = 'Searching for subtitles... ';
            apiRoute('home/manualSearchSubtitles', { params: subtitleParams }) // eslint-disable-line no-undef
                .then(response => {
                    if (response.data.result === 'success') {
                        this.subtitles.push(...response.data.subtitles);
                    }
                }).catch(error => {
                    console.log(`Error trying to search for subtitles. Error: ${error}`);
                }).finally(() => {
                    this.loading = false;
                });
        },
        pickSubtitle(subtitleId) {
            // Download and save this subtitle with the episode.
            const { season, episode } = this;
            const params = {
                ...subtitleParams, // This is the computed property
                picked_id: subtitleId // eslint-disable-line camelcase
            }

            this.displayQuestion = false;
            this.loadingMessage = 'downloading subtitle... ';
            this.loading = true;

            apiRoute('home/manualSearchSubtitles', { params }) // eslint-disable-line no-undef
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
                    // Cleanup
                    this.loadingMessage = '';
                    this.loading = false;
                    this.close();
                });
        },
        close() {
            this.$emit('close', this);
            // Destroy the vue listeners, etc
            this.$destroy();
            // Remove the element from the DOM
            this.$el.parentNode.removeChild(this.$el);
        }
    }
};
</script>
<style scoped>
.subtitle-search-wrapper {
    display: table-row;
    column-span: all;
}

.subtitle-search-wrapper >>> table.subtitle-table tr {
    background-color: rgb(190, 222, 237);
}

.subtitle-search-wrapper > td {
    padding: 0;
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
