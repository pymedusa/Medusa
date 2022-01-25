<template>
    <div id="search-template-container">
        <vue-snotify />
        <!-- Display the default episode search templates -->
        <div class="form-group">
            <div class="row">
                <div class="col-sm-2">
                    <label for="default_templates" class="control-label">
                        <span>Default Episode Templates</span>
                    </label>
                </div>
                <div class="col-sm-10 content">
                    <search-template-pattern
                        v-for="template in defaultEpisodeTemplates"
                        v-bind="{ template, format: showFormat, animeType }"
                        :key="template.id"
                    />
                </div>
            </div>
        </div>

        <!-- Display the default season search templates -->
        <div class="form-group">
            <div class="row">
                <div class="col-sm-2">
                    <label for="default_templates" class="control-label">
                        <span>Default Season Templates</span>
                    </label>
                </div>
                <div class="col-sm-10 content">
                    <search-template-pattern
                        v-for="template in defaultSeasonTemplates"
                        v-bind="{ template, format: showFormat, animeType }"
                        :key="template.id"
                    />
                </div>
            </div>
        </div>

        <!-- Display the custom templates -->
        <div class="form-group">
            <div class="row">
                <div class="col-sm-2">
                    <label for="default_templates" class="control-label">
                        <span>Custom Templates</span>
                    </label>
                </div>
                <div class="col-sm-10 content">
                    <search-template-pattern
                        v-for="template in customTemplates"
                        v-bind="{ template, format: showFormat, animeType }"
                        :key="template.template" @remove="remove"
                    />
                </div>
            </div>
        </div>

        <search-template-custom
            v-bind="{ show, animeType, format: showFormat }"
            @input="add"
        />

        <!-- Anime only -->
        <div v-show="showFormat === 'anime'">
            <div class="row">
                <div v-if="animeType > 0" class="form-group">
                    <label for="naming_anime" class="col-sm-2 control-label">
                        <span>Add Absolute Number</span>
                    </label>
                    <div class="col-sm-10 content">
                        <input
                            type="radio"
                            name="naming_anime"
                            id="naming_anime"
                            :value="1"
                            v-model="animeType"
                        >
                        <span>Add the absolute number to the season/episode format?</span>
                        <p>Only applies to animes. (e.g. S15E45 - 310 vs S15E45)</p>
                    </div>
                </div>
            </div>

            <div class="row">
                <div v-if="animeType > 0" class="form-group">
                    <label for="naming_anime_only" class="col-sm-2 control-label">
                        <span>Only Absolute Number</span>
                    </label>
                    <div class="col-sm-10 content">
                        <input
                            type="radio"
                            name="naming_anime"
                            id="naming_anime_only"
                            :value="2"
                            v-model="animeType"
                        >
                        <span>Replace season/episode format with absolute number</span>
                        <p>Only applies to animes.</p>
                    </div>
                </div>
            </div>

            <div class="row">
                <div v-if="animeType > 0" class="form-group">
                    <label for="naming_anime_none" class="col-sm-2 control-label">
                        <span>No Absolute Number</span>
                    </label>
                    <div class="col-sm-10 content">
                        <input
                            type="radio"
                            name="naming_anime"
                            id="naming_anime_none"
                            :value="3"
                            v-model="animeType"
                        >
                        <span>Don't include the absolute number</span>
                        <p>Only applies to animes.</p>
                    </div>
                </div>
            </div>
        </div>

        <div id="naming-key" class="nocheck">
            <table class="Key">
                <thead>
                    <tr>
                        <th class="align-right">Meaning</th>
                        <th>Pattern</th>
                        <th width="60%">Result</th>
                    </tr>
                </thead>
                <tfoot>
                    <tr>
                        <th colspan="3">
                            Use lower case if you want lower case names (eg.
                            %sn, %e.n, %q_n etc)
                        </th>
                    </tr>
                </tfoot>
                <tbody>
                    <tr>
                        <td class="align-right">
                            <b>Show Name:</b>
                        </td>
                        <td>%SN</td>
                        <td>Show Name</td>
                    </tr>
                    <tr class="even">
                        <td>&nbsp;</td>
                        <td>%S.N</td>
                        <td>Show.Name</td>
                    </tr>
                    <tr>
                        <td>&nbsp;</td>
                        <td>%S_N</td>
                        <td>Show_Name</td>
                    </tr>
                    <tr class="even">
                        <td class="align-right">
                            <b>Season Number:</b>
                        </td>
                        <td>%S</td>
                        <td>2</td>
                    </tr>
                    <tr>
                        <td>&nbsp;</td>
                        <td>%0S</td>
                        <td>02</td>
                    </tr>
                    <tr class="even">
                        <td class="align-right">
                            <b>XEM Season Number:</b>
                        </td>
                        <td>%XS</td>
                        <td>2</td>
                    </tr>
                    <tr>
                        <td>&nbsp;</td>
                        <td>%0XS</td>
                        <td>02</td>
                    </tr>
                    <tr class="even">
                        <td class="align-right">
                            <b>Episode Number:</b>
                        </td>
                        <td>%E</td>
                        <td>3</td>
                    </tr>
                    <tr>
                        <td>&nbsp;</td>
                        <td>%0E</td>
                        <td>03</td>
                    </tr>
                    <tr class="even">
                        <td class="align-right">
                            <b>XEM Episode Number:</b>
                        </td>
                        <td>%XE</td>
                        <td>3</td>
                    </tr>
                    <tr>
                        <td>&nbsp;</td>
                        <td>%0XE</td>
                        <td>03</td>
                    </tr>
                    <tr class="even">
                        <td class="align-right">
                            <b>Absolute Episode Number:</b>
                        </td>
                        <td>%AB</td>
                        <td>003</td>
                    </tr>
                    <tr>
                        <td class="align-right">
                            <b>Xem Absolute Episode Number:</b>
                        </td>
                        <td>%XAB</td>
                        <td>003</td>
                    </tr>
                    <tr class="even">
                        <td class="align-right">
                            <b>Episode Name:</b>
                        </td>
                        <td>%EN</td>
                        <td>Episode Name</td>
                    </tr>
                    <tr>
                        <td>&nbsp;</td>
                        <td>%E.N</td>
                        <td>Episode.Name</td>
                    </tr>
                    <tr class="even">
                        <td>&nbsp;</td>
                        <td>%E_N</td>
                        <td>Episode_Name</td>
                    </tr>
                    <tr>
                        <td class="align-right">
                            <b>Air Date:</b>
                        </td>
                        <td>%M</td>
                        <td>{{ getDateFormat('M') }}</td>
                    </tr>
                    <tr class="even">
                        <td>&nbsp;</td>
                        <td>%D</td>
                        <td>{{ getDateFormat('d') }}</td>
                    </tr>
                    <tr>
                        <td>&nbsp;</td>
                        <td>%Y</td>
                        <td>{{ getDateFormat('yyyy') }}</td>
                    </tr>
                    <tr>
                        <td class="align-right">
                            <b>Post-Processing Date:</b>
                        </td>
                        <td>%CM</td>
                        <td>{{ getDateFormat('M') }}</td>
                    </tr>
                    <tr class="even">
                        <td>&nbsp;</td>
                        <td>%CD</td>
                        <td>{{ getDateFormat('d') }}</td>
                    </tr>
                    <tr>
                        <td>&nbsp;</td>
                        <td>%CY</td>
                        <td>{{ getDateFormat('yyyy') }}</td>
                    </tr>
                    <tr>
                        <td class="align-right">
                            <b>Quality:</b>
                        </td>
                        <td>%QN</td>
                        <td>720p BluRay</td>
                    </tr>
                    <tr class="even">
                        <td>&nbsp;</td>
                        <td>%Q.N</td>
                        <td>720p.BluRay</td>
                    </tr>
                    <tr>
                        <td>&nbsp;</td>
                        <td>%Q_N</td>
                        <td>720p_BluRay</td>
                    </tr>
                    <tr>
                        <td class="align-right">
                            <b>Scene Quality:</b>
                        </td>
                        <td>%SQN</td>
                        <td>720p HDTV x264</td>
                    </tr>
                    <tr class="even">
                        <td>&nbsp;</td>
                        <td>%SQ.N</td>
                        <td>720p.HDTV.x264</td>
                    </tr>
                    <tr>
                        <td>&nbsp;</td>
                        <td>%SQ_N</td>
                        <td>720p_HDTV_x264</td>
                    </tr>
                    <tr class="even">
                        <td class="align-right">
                            <i
                                class="glyphicon glyphicon-info-sign"
                                title="Multi-EP style is ignored"
                            />
                            <b>Release Name:</b>
                        </td>
                        <td>%RN</td>
                        <td>Show.Name.S02E03.HDTV.x264-RLSGROUP</td>
                    </tr>
                    <tr>
                        <td class="align-right">
                            <i
                                class="glyphicon glyphicon-info-sign"
                                title="UNKNOWN_RELEASE_GROUP is used in place of RLSGROUP if it could not be properly detected"
                            />
                            <b>Release Group:</b>
                        </td>
                        <td>%RG</td>
                        <td>RLSGROUP</td>
                    </tr>
                    <tr class="even">
                        <td class="align-right">
                            <i
                                class="glyphicon glyphicon-info-sign"
                                title="If episode is proper/repack add 'proper' to name."
                            />
                            <b>Release Type:</b>
                        </td>
                        <td>%RT</td>
                        <td>PROPER</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<script>
import formatDate from 'date-fns/format';
import SearchTemplateCustom from './search-template-custom';
import SearchTemplatePattern from './search-template-pattern';
import { mapActions } from 'vuex';

export default {
    name: 'search-template-container',
    components: {
        SearchTemplateCustom,
        SearchTemplatePattern
    },
    props: {
        show: {
            type: Object,
            default: null
        }
    },
    data() {
        return {
            animeType: 3,
            newTemplate: '',
            newTemplateShowExample: false,
            newTemplateEnabled: true
        };
    },
    computed: {
        searchTemplates() {
            const { show } = this;
            const { config } = show;
            const { searchTemplates } = config;
            return searchTemplates;
        },
        defaultEpisodeTemplates() {
            const { searchTemplates } = this;

            if (!searchTemplates) {
                return [];
            }

            return searchTemplates.filter(
                template => template.default && !template.seasonSearch
            );
        },
        defaultSeasonTemplates() {
            const { searchTemplates } = this;

            if (!searchTemplates) {
                return [];
            }

            return searchTemplates.filter(
                template => template.default && template.seasonSearch
            );
        },

        customTemplates() {
            const { searchTemplates } = this;

            if (!searchTemplates) {
                return [];
            }

            return searchTemplates.filter(template => !template.default);
        },
        /**
         * Provide the custom naming type. -Like sports, anime, air by date- description.
         * If none provided we asume this is the default episode naming component.
         * And that means there will be no checkbox available to enable/disable it.
         *
         * @returns {String} - The selected show format as one of the options: anime, sports or airByDate.
         */
        showFormat() {
            const { show } = this;
            const { config } = show;
            return ['anime', 'sports', 'airByDate'].find(item => config[item]);
        }
    },
    methods: {
        ...mapActions([
            'addSearchTemplate',
            'removeSearchTemplate'
        ]),
        getDateFormat(format) {
            return formatDate(new Date(), format);
        },
        update() {
            const { templates, format } = this;
            this.$nextTick(() => {
                this.$emit('change', {
                    templates,
                    format
                });
            });
        },
        add(template) {
            /**
             * Add new template to the array of searchTemplates.
             */
            const { show, addSearchTemplate } = this;
            if (this.searchTemplates.find(t => t.template === template.pattern && t.title === template.title)) {
                this.$snotify.error(
                    'Error while trying to add the template',
                    "Can't add a pattern that already exists!"
                );
                return;
            }

            // Use vuex action to commit the new template.
            addSearchTemplate({ show, template: {
                title: template.title.title,
                template: template.pattern,
                enabled: template.enabled,
                season: template.title.season,
                default: false,
                seasonSearch: template.seasonSearch
            } });

            this.update();
        },
        /**
         * Remove a "custom" search template from the shows searchTemplates array.
         * @param {object} template - Search template object.
         */
        remove(template) {
            const { show, removeSearchTemplate } = this;
            removeSearchTemplate({ show, template });

            this.update();
        }
    }
};
</script>
<style>
#naming-key {
    margin: 20px 0 20px 0;
}

.template-container {
    padding-left: 40px;
}

.show-template {
    left: -8px;
    top: 4px;
    position: absolute;
    z-index: 10;
    opacity: 0.6;
}

.move-down {
    transform: translateY(10px);
}
</style>
