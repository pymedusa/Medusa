<template>
    <div id="search-template-custom" class="form-group">
        <!-- Display add a new tempalte input -->
        <div class="row">
            <div class="col-sm-2">
                <label for="default_templates" class="control-label">
                    <span>Add Custom Template</span>
                </label>
            </div>
        </div>
        <div class="row">
            <div class="col-lg-12 content">
                <div class="row">
                    <div class="col-sm-2">
                        <label class="control-label">
                            <span>Title:</span>
                        </label>
                    </div>
                    <div class="col-sm-10 content">
                        <select
                            id="default_page"
                            name="default_page"
                            v-model="selectedTitle"
                            class="form-control input-sm"
                        >
                            <option
                                :value="option"
                                v-for="option in selectTitles"
                                :key="option.title"
                            >{{ titleOptionDescription(option) }}
                            </option>
                        </select>
                    </div>
                </div>

                <div class="row">
                    <div class="col-sm-2">
                        <label class="control-label">
                            <span>Episode or Season search:</span>
                        </label>
                    </div>
                    <div class="col-sm-10">
                        <div class="checkbox">
                            <label for="episode">Episode</label>
                            <input
                                type="radio"
                                id="episode"
                                :value="'episode'"
                                v-model="episodeOrSeason"
                            >
                            <label for="episode">Season</label>
                            <input
                                type="radio"
                                id="season"
                                :value="'season'"
                                v-model="episodeOrSeason"
                            >

                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-sm-2">
                        <label class="control-label">
                            <span>Search Template:</span>
                        </label>
                    </div>
                    <div class="col-sm-10 pattern">
                        <span ref="inputTitle" v-if="selectedTitle">%SN</span>
                        <input
                            type="text"
                            name="new_pattern"
                            v-model="addPattern"
                            class="form-control-inline-max input-sm max-input350 search-pattern"
                            style="padding-left: 50px"
                            :disabled="!selectedTitle"
                        >
                        <input type="checkbox" v-model="enabled">
                        <p v-if="!validated && isValidMessage">{{isValidMessage}}</p>
                    </div>
                </div>

                <div class="row">
                    <div class="col-sm-2">
                        <label class="control-label">
                            <span>example:</span>
                        </label>
                    </div>
                    <div class="col-sm-10" :class="{ 'error-message': !validated }">
                        {{ patternExample }}
                    </div>
                </div>

                <div class="row">
                    <div class="col-sm-2" />
                    <div class="col-sm-10 vertical-align">
                        <input
                            id="submit"
                            type="submit"
                            value="Add custom exception"
                            class="btn-medusa pull-left button"
                            :disabled="!validated"
                            @click="add"
                        >
                        <p>{{ notification }}</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { mapState } from 'vuex';
import { VTooltip } from 'v-tooltip';
import AsyncComputed from 'vue-async-computed';
import debounce from 'lodash/debounce';

export default {
    name: 'search-template-custom',
    directives: {
        tooltip: VTooltip
    },
    plugins: {
        AsyncComputed
    },
    props: {
        /**
         * Provide the custom naming type. -Like sports, anime, air by date- description.
         * If none provided we asume this is the default episode naming component.
         * And that means there will be no checkbox available to enable/disable it.
         */
        format: {
            type: String,
            default: ''
        },
        show: {
            type: Object,
            default: null
        },
        animeType: {
            type: Number,
            default: 3
        }
    },
    data() {
        return {
            showFormat: null,
            patternExample: '',
            validated: false,
            isValidMessage: '',
            seasonPattern: false,
            showExample: false,

            selectedTitle: null,
            addPattern: '',
            enabled: true,
            separator: ' ',
            episodeOrSeason: 'episode',
            notification: ''
        };
    },
    watch: {
        addPattern(newPattern) {
            if (!newPattern) {
                return;
            }
            this.notification =
                'testing the pattern as soon as you stop typing';
            this.debouncedIsValid();
            this.debouncedTestNaming();
        }
    },
    created() {
        this.debouncedIsValid = debounce(this.isValid, 500);
        this.debouncedTestNaming = debounce(this.testNaming, 500);
    },
    mounted() {
        const { show } = this;
        const { title } = show;

        this.selectedTitle = {
            indexer: show.indexer,
            seriesId: show.id[show.indexer],
            season: -1,
            title
        };
    },
    computed: {
        ...mapState({
            client: state => state.auth.client
        }),
        selectTitles() {
            const { show } = this;
            const { config, title } = show;
            const { aliases } = config;

            const titleOption = {
                indexer: show.indexer,
                seriesId: show.id[show.indexer],
                season: -1,
                title
            };

            return [...[titleOption], ...aliases];
        },
        templateExists() {
            const { addPattern, selectedTitle, show } = this;
            const { config } = show;
            const combinedPattern = `%SN${addPattern}`;
            return config.searchTemplates.find(
                template => template.title === selectedTitle.title &&
                template.season === selectedTitle.season &&
                template.template === combinedPattern
            );
        }
    },
    methods: {
        titleOptionDescription(option) {
            let seasonDescription = '';

            if (option.season > -1) {
                seasonDescription = ` (Season ${option.season} exception)`;
            }

            return option.title + seasonDescription;
        },
        async testNaming() {
            const { animeType, addPattern, format, selectedTitle } = this;
            if (!addPattern) {
                return;
            }

            console.debug(`Test pattern ${addPattern}`);

            const combinedPattern = `${selectedTitle.title}${addPattern}`;

            let params = {
                pattern: combinedPattern
            };

            const formatMap = new Map([
                // eslint-disable-next-line camelcase
                ['anime', { anime_type: animeType }],
                ['sports', { sports: true }],
                ['airByDate', { abd: true }]
            ]);

            if (format !== '') {
                params = { ...params, ...formatMap.get(format) };
            }

            let response = '';

            try {
                response = await this.client.apiRoute.get(
                    'config/postProcessing/testNaming',
                    {
                        params,
                        timeout: 20000
                    }
                );
                this.patternExample = response.data;
            } catch (error) {
                console.warn(error);
            }
        },
        isValid() {
            const { addPattern } = this;
            if (!addPattern) {
                return;
            }

            if (!(addPattern.startsWith(' ') || addPattern.startsWith('.'))) {
                this.validated = false;
                this.isValidMessage = 'Dont forget to start the pattern with a separator. For example a dot or space.';
                return;
            }

            if (this.templateExists) {
                this.validated = false;
                this.isValidMessage = 'This template combination is already in use';
                return;
            }

            this.validated = true;
            this.isValidMessage = '';
        },
        add() {
            const {
                show,
                addPattern,
                episodeOrSeason,
                enabled,
                selectedTitle
            } = this;
            const { title } = show;

            this.$emit('input', {
                pattern: `%SN${addPattern}`,
                seasonSearch: episodeOrSeason === 'season',
                enabled,
                title: selectedTitle
            });

            this.selectedTitle = {
                indexer: show.indexer,
                seriesId: show.id[show.indexer],
                season: -1,
                title
            };
            this.addPattern = '';
            this.episodeOrSeason = 'episode';
        }
    }
};
</script>
<style scoped>
.show-template {
    left: -8px;
    top: 4px;
    position: absolute;
    z-index: 10;
    opacity: 0.6;
}

.template-example {
    display: block;
    line-height: 20px;
    margin-bottom: 15px;
    padding: 2px 5px 2px 2px;
    clear: left;
    max-width: 338px;
}

.tooltip-wrapper {
    min-width: 340px;
}

.invalid {
    background-color: #ff5b5b;
}

.error-message {
    color: red;
}

.tooltip {
    display: block !important;
    z-index: 10000;
}

.tooltip .tooltip-inner {
    background: #ffef93;
    color: #555;
    border-radius: 16px;
    padding: 5px 10px 4px;
    border: 1px solid #f1d031;
    -webkit-box-shadow: 1px 1px 3px 1px rgba(0, 0, 0, 0.15);
    -moz-box-shadow: 1px 1px 3px 1px rgba(0, 0, 0, 0.15);
    box-shadow: 1px 1px 3px 1px rgba(0, 0, 0, 0.15);
}

.tooltip .tooltip-arrow {
    width: 0;
    height: 0;
    position: absolute;
    margin: 5px;
    border: 1px solid #ffef93;
    z-index: 1;
}

.tooltip[x-placement^='top'] {
    margin-bottom: 5px;
}

.tooltip[x-placement^='top'] .tooltip-arrow {
    border-width: 5px 5px 0 5px;
    border-left-color: transparent !important;
    border-right-color: transparent !important;
    border-bottom-color: transparent !important;
    bottom: -5px;
    left: calc(50% - 4px);
    margin-top: 0;
    margin-bottom: 0;
}

.tooltip[x-placement^='bottom'] {
    margin-top: 5px;
}

.tooltip[x-placement^='bottom'] .tooltip-arrow {
    border-width: 0 5px 5px 5px;
    border-left-color: transparent !important;
    border-right-color: transparent !important;
    border-top-color: transparent !important;
    top: -5px;
    left: calc(50% - 4px);
    margin-top: 0;
    margin-bottom: 0;
}

.tooltip[x-placement^='right'] {
    margin-left: 5px;
}

.tooltip[x-placement^='right'] .tooltip-arrow {
    border-width: 5px 5px 5px 0;
    border-left-color: transparent !important;
    border-top-color: transparent !important;
    border-bottom-color: transparent !important;
    left: -4px;
    top: calc(50% - 5px);
    margin-left: 0;
    margin-right: 0;
}

.tooltip[x-placement^='left'] {
    margin-right: 5px;
}

.tooltip[x-placement^='left'] .tooltip-arrow {
    border-width: 5px 0 5px 5px;
    border-top-color: transparent !important;
    border-right-color: transparent !important;
    border-bottom-color: transparent !important;
    right: -4px;
    top: calc(50% - 5px);
    margin-left: 0;
    margin-right: 0;
}

.tooltip.popover .popover-inner {
    background: #ffef93;
    color: #555;
    padding: 24px;
    border-radius: 5px;
    box-shadow: 0 5px 30px rgba(black, 0.1);
}

.tooltip.popover .popover-arrow {
    border-color: #ffef93;
}

.tooltip[aria-hidden='true'] {
    visibility: hidden;
    opacity: 0;
    transition: opacity 0.15s, visibility 0.15s;
}

.tooltip[aria-hidden='false'] {
    visibility: visible;
    opacity: 1;
    transition: opacity 0.15s;
}

.vertical-align {
    display: flex;
    align-items: center;
}

.vertical-align > p {
    margin: auto 10px;
}

.pattern > span {
    position: absolute;
    top: 0;
    left: 25px;
    color: black;
    background-color: grey;
    padding: 1px 5px;
    opacity: 0.8;
    border-radius: 5px;
}

.pattern {
    position: relative;
}
</style>
