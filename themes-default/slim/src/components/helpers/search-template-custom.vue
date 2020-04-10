<template>
    <div id="search-template-custom">
        <!-- Display add a new tempalte input -->
        <div class="row">
            <div class="form-group">
                <label for="default_templates" class="col-sm-2 control-label">
                    <span>Add Custom Template</span>
                </label>
                <div class="col-sm-10 content">
                    <div class="row">
                        <div class="col-sm-12">
                            <div class="form-group">
                                <label class="col-sm-2">
                                    <span>Title:</span>
                                </label>
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
                                            >{{
                                                titleOptionDescription(option)
                                            }}
                                        </option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="row">
                        <div class="col-sm-12">
                            <div class="form-group">
                                <label class="col-sm-2">
                                    <span>Episode or Season search:</span>
                                </label>
                                <div class="col-sm-10">
                                    <label for="episode">Episode</label>
                                    <input
                                        type="radio"
                                        id="episode"
                                        :value="'episode'"
                                        v-model="episodeOrSeason"
                                    />
                                    <label for="episode">Season</label>
                                    <input
                                        type="radio"
                                        id="season"
                                        :value="'season'"
                                        v-model="episodeOrSeason"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="row">
                        <div class="col-sm-12">
                            <div class="form-group">
                                <label class="col-sm-2">
                                    <span>Pattern:</span>
                                </label>
                                <div class="col-sm-10">
                                    <input
                                        type="text"
                                        name="new_pattern"
                                        v-model="addPattern"
                                        class="form-control-inline-max input-sm max-input350 search-pattern"
                                    />
                                    <input type="checkbox" v-model="enabled" />
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="row">
                        <div class="col-sm-12">
                            <div class="form-group">
                                <label class="col-sm-2">
                                    <span>example:</span>
                                </label>
                                <div class="col-sm-10">
                                    {{ patternExample }}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="row">
                        <div class="col-sm-12">
                            <div class="form-group">
                                <div class="col-sm-10 .offset-sm-2">
                                    <input
                                        id="submit"
                                        type="submit"
                                        value="Add custom exception"
                                        class="btn-medusa pull-left button"
                                        :disabled="!validated"
                                        @click="add"
                                    />
                                    <p>{{ notification }}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import formatDate from 'date-fns/format';
import { apiRoute } from '../../api';
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
        combinedPattern(newPattern, oldPattern) {
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
    computed: {
        combinedPattern() {
            const { separator, selectedTitle, addPattern } = this;
            if (!selectedTitle || !addPattern) {
                return '';
            }
            return `${selectedTitle.title}${separator}${addPattern}`;
        },
        selectTitles() {
            const { show } = this;
            const { config, title } = show;
            const { aliases } = config;

            const titleOption = {
                indexer: show.indexer,
                seriesId: show.id[show.indexer],
                season: -1,
                title: title
            };

            return [...[titleOption], ...aliases];
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
            const { animeType, combinedPattern, format } = this;
            if (!combinedPattern) {
                return;
            }

            console.debug(`Test pattern ${combinedPattern}`);

            let params = {
                pattern: combinedPattern
            };

            const formatMap = new Map([
                ['anime', { anime_type: animeType }],
                ['sports', { sports: true }],
                ['airByDate', { abd: true }]
            ]);

            if (format !== '') {
                params = { ...params, ...formatMap.get(format) };
            }

            let response = '';

            try {
                response = await apiRoute.get(
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
        async isValid() {
            const { animeType, combinedPattern, showFormat } = this;
            if (!combinedPattern) {
                return;
            }

            let params = {
                pattern: combinedPattern
            };
            const formatMap = new Map([
                ['anime', { anime_type: animeType }],
                ['sports', { sports: true }],
                ['airByDate', { abd: true }]
            ]);

            if (showFormat !== '') {
                params = { ...params, ...formatMap.get(showFormat) };
            }

            try {
                const response = await apiRoute.get(
                    'config/postProcessing/isNamingValid',
                    { params, timeout: 20000 }
                );
                if (response.data !== 'invalid') {
                    this.validated = true;
                    return;
                }
            } catch (error) {
                console.warn(error);
            }
            this.validated = false;
        },
        add() {
            const {
                combinedPattern,
                episodeOrSeason,
                enabled,
                selectedTitle
            } = this;
            this.$emit('input', {
                pattern: combinedPattern,
                seasonSearch: episodeOrSeason === 'season',
                enabled,
                title: selectedTitle
            });

            this.selectedTitle = '';
            this.addPattern = '';
            this.episodeOrSeason = 'episode';
        }
    }
};
</script>
<style>
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
    float: left;
    min-width: 340px;
}

.invalid {
    background-color: #ff5b5b;
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
</style>
