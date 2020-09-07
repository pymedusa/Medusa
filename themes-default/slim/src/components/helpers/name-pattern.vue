<template>
    <div id="name-pattern-wrapper">
        <!-- If a 'type' is passed, it means that where checking a custom naming pattern. As for example sports, air-by-date etc.
        In that case, we're showing this checkbox, to display the rest of the form.
        If type evaulates to an empty string, we're asuming this is the default name pattern. And it's enabled by default. -->
        <div v-if="type" class="form-group">
            <label for="enable_naming_custom" class="col-sm-2 control-label">
                <span>Custom {{ type }}</span>
            </label>
            <div class="col-sm-10 content">
                <toggle-button :width="45" :height="22" id="enable_naming_custom" name="enable_naming_custom" v-model="isEnabled" @input="update()" sync />
                <span>Name {{ type }} shows differently than regular shows?</span>
            </div>
        </div>

        <div v-if="!type || isEnabled" class="episode-naming">
            <div class="form-group">
                <label for="name_presets" class="col-sm-2 control-label">
                    <span>Name Pattern:</span>
                </label>
                <div class="col-sm-10 content">
                    <select id="name_presets" class="form-control input-sm" v-model="selectedNamingPattern" @change="updatePatternSamples" @input="update()">
                        <option :id="preset.pattern" v-for="preset in presets" :key="preset.pattern">{{ preset.example }}</option>
                    </select>
                </div>
            </div>

            <div id="naming_custom">
                <div v-if="isCustom" class="form-group" style="padding-top: 0;">
                    <label class="col-sm-2 control-label">
                        <span>&nbsp;</span>
                    </label>
                    <div class="col-sm-10 content">
                        <input type="text" name="naming_pattern" id="naming_pattern" v-model="customName" @change="updatePatternSamples" @input="update()" class="form-control-inline-max input-sm max-input350">
                        <img src="images/legend16.png" width="16" height="16" alt="[Toggle Key]" id="show_naming_key" title="Toggle Naming Legend" class="legend" @click="showLegend = !showLegend">
                    </div>
                </div>

                <div id="naming_key" class="nocheck" v-if="showLegend && isCustom">
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
                                <th colspan="3">Use lower case if you want lower case names (eg. %sn, %e.n, %q_n etc)</th>
                            </tr>
                        </tfoot>
                        <tbody>
                            <tr>
                                <td class="align-right"><b>Show Name:</b></td>
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
                                <td class="align-right"><b>Season Number:</b></td>
                                <td>%S</td>
                                <td>2</td>
                            </tr>
                            <tr>
                                <td>&nbsp;</td>
                                <td>%0S</td>
                                <td>02</td>
                            </tr>
                            <tr class="even">
                                <td class="align-right"><b>XEM Season Number:</b></td>
                                <td>%XS</td>
                                <td>2</td>
                            </tr>
                            <tr>
                                <td>&nbsp;</td>
                                <td>%0XS</td>
                                <td>02</td>
                            </tr>
                            <tr class="even">
                                <td class="align-right"><b>Episode Number:</b></td>
                                <td>%E</td>
                                <td>3</td>
                            </tr>
                            <tr>
                                <td>&nbsp;</td>
                                <td>%0E</td>
                                <td>03</td>
                            </tr>
                            <tr class="even">
                                <td class="align-right"><b>XEM Episode Number:</b></td>
                                <td>%XE</td>
                                <td>3</td>
                            </tr>
                            <tr>
                                <td>&nbsp;</td>
                                <td>%0XE</td>
                                <td>03</td>
                            </tr>
                            <tr class="even">
                                <td class="align-right"><b>Absolute Episode Number:</b></td>
                                <td>%AB</td>
                                <td>003</td>
                            </tr>
                            <tr>
                                <td class="align-right"><b>Xem Absolute Episode Number:</b></td>
                                <td>%XAB</td>
                                <td>003</td>
                            </tr>
                            <tr class="even">
                                <td class="align-right"><b>Episode Name:</b></td>
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
                                <td class="align-right"><b>Air Date:</b></td>
                                <td>%M</td>
                                <td>{{ getDateFormat('M') }}</td>
                            </tr>
                            <tr class="even">
                                <td>&nbsp;</td>
                                <td>%D</td>
                                <td>{{ getDateFormat('d')}}</td>
                            </tr>
                            <tr>
                                <td>&nbsp;</td>
                                <td>%Y</td>
                                <td>{{ getDateFormat('yyyy')}}</td>
                            </tr>
                            <tr>
                                <td class="align-right"><b>Post-Processing Date:</b></td>
                                <td>%CM</td>
                                <td>{{ getDateFormat('M') }}</td>
                            </tr>
                            <tr class="even">
                                <td>&nbsp;</td>
                                <td>%CD</td>
                                <td>{{ getDateFormat('d')}}</td>
                            </tr>
                            <tr>
                                <td>&nbsp;</td>
                                <td>%CY</td>
                                <td>{{ getDateFormat('yyyy')}}</td>
                            </tr>
                            <tr>
                                <td class="align-right"><b>Quality:</b></td>
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
                                <td class="align-right"><b>Scene Quality:</b></td>
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
                                <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="Multi-EP style is ignored" /> <b>Release Name:</b></td>
                                <td>%RN</td>
                                <td>Show.Name.S02E03.HDTV.x264-RLSGROUP</td>
                            </tr>
                            <tr>
                                <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="UNKNOWN_RELEASE_GROUP is used in place of RLSGROUP if it could not be properly detected" /> <b>Release Group:</b></td>
                                <td>%RG</td>
                                <td>RLSGROUP</td>
                            </tr>
                            <tr class="even">
                                <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="If episode is proper/repack add 'proper' to name." /> <b>Release Type:</b></td>
                                <td>%RT</td>
                                <td>PROPER</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div v-if="selectedMultiEpStyle" class="form-group">
                <label class="col-sm-2 control-label" for="naming_multi_ep">
                    <span>Multi-Episode Style:</span>
                </label>
                <div class="col-sm-10 content">
                    <select id="naming_multi_ep" name="naming_multi_ep" v-model="selectedMultiEpStyle" class="form-control input-sm" @change="updatePatternSamples" @input="update($event)">
                        <option id="multiEpStyle" :value="multiEpStyle.value" v-for="multiEpStyle in availableMultiEpStyles" :key="multiEpStyle.value">{{ multiEpStyle.text }}</option>
                    </select>
                </div>
            </div>

            <div class="form-group row">
                <h3 class="col-sm-12">Single-EP Sample:</h3>
                <div class="example col-sm-12">
                    <span class="jumbo" id="naming_example">{{ namingExample }}</span>
                </div>
            </div>
            <div v-if="isMulti" class="form-group row">
                <h3 class="col-sm-12">Multi-EP sample:</h3>
                <div class="example col-sm-12">
                    <span class="jumbo" id="naming_example_multi">{{ namingExampleMulti }}</span>
                </div>
            </div>

            <!-- Anime only -->
            <div v-if="animeType > 0" class="form-group">
                <label for="naming_anime" class="col-sm-2 control-label">
                    <span>Add Absolute Number</span>
                </label>
                <div class="col-sm-10 content">
                    <input type="radio" name="naming_anime" id="naming_anime" value="1" v-model="animeType" @change="updatePatternSamples">
                    <span>Add the absolute number to the season/episode format?</span>
                    <p>Only applies to animes. (e.g. S15E45 - 310 vs S15E45)</p>
                </div>
            </div>

            <div v-if="animeType > 0" class="form-group">
                <label for="naming_anime_only" class="col-sm-2 control-label">
                    <span>Only Absolute Number</span>
                </label>
                <div class="col-sm-10 content">
                    <input type="radio" name="naming_anime" id="naming_anime_only" value="2" v-model="animeType" @change="updatePatternSamples">
                    <span>Replace season/episode format with absolute number</span>
                    <p>Only applies to animes.</p>
                </div>
            </div>

            <div v-if="animeType > 0"  class="form-group">
                <label for="naming_anime_none" class="col-sm-2 control-label">
                    <span>No Absolute Number</span>
                </label>
                <div class="col-sm-10 content">
                    <input type="radio" name="naming_anime" id="naming_anime_none" value="3" v-model="animeType" @change="updatePatternSamples">
                    <span>Don't include the absolute number</span>
                    <p>Only applies to animes.</p>
                </div>
            </div>
        </div>

    </div>
</template>

<script>
import formatDate from 'date-fns/format';
import { ToggleButton } from 'vue-js-toggle-button';
import { apiRoute } from '../../api';

export default {
    name: 'name-pattern',
    components: {
        ToggleButton
    },
    props: {
        /**
         * Current naming pattern.
         */
        namingPattern: {
            type: String,
            default: ''
        },
        /**
         * An array of available preset naming patterns.
         */
        namingPresets: {
            type: Array,
            default: () => []
        },
        /**
         * The selected multi ep style
         */
        multiEpStyle: {
            type: Number
        },
        /**
         * Availale multi ep style
         */
        multiEpStyles: {
            type: Array,
            default: () => []
        },
        /**
         * For anime shows there are a number of variations on how the absolute episode number
         * is added to the episode.
         */
        animeNamingType: {
            type: Number,
            default: 0
        },
        /**
         * Provide the custom naming type. -Like sports, anime, air by date- description.
         * If none provided we asume this is the default episode naming component.
         * And that means there will be no checkbox available to enable/disable it.
         */
        type: {
            type: String,
            default: ''
        },
        /**
         * Used icw with the type property.
         * If a type has been passed, the `enabled` property can be used to toggle the visibilty of the name-pattern settings.
         */
        enabled: {
            type: Boolean,
            default: true
        },
        flagLoaded: {
            type: Boolean,
            default: false
        }
    },
    data() {
        return {
            presets: [],
            availableMultiEpStyles: [],
            pattern: '',
            customName: '',
            showLegend: false,
            namingExample: '',
            namingExampleMulti: '',
            isEnabled: false,
            selectedMultiEpStyle: 1,
            animeType: 0,
            lastSelectedPattern: ''
        };
    },
    methods: {
        getDateFormat(format) {
            return formatDate(new Date(), format);
        },
        testNaming(pattern, selectedMultiEpStyle, animeType) {
            console.debug(`Test pattern ${pattern} for ${(selectedMultiEpStyle) ? 'multi' : 'single ep'}`);
            const params = {
                pattern,
                anime_type: animeType // eslint-disable-line camelcase
            };

            if (selectedMultiEpStyle) {
                params.multi = selectedMultiEpStyle;
            }

            try {
                return apiRoute.get('config/postProcessing/testNaming', { params, timeout: 20000 }).then(res => res.data);
            } catch (error) {
                console.warn(error);
                return '';
            }
        },
        updatePatternSamples() {
            // If it's a custom pattern, we need to get the custom pattern from this.customName
            // if customName if empty for whatever reason, just use the last selected preset value.
            if (!this.customName) {
                this.customName = this.lastSelectedPattern;
            }

            const pattern = this.isCustom ? this.customName : this.pattern;

            // Exiting early as we probably don't have all the properties yet.
            // updatePatternSamples() can be triggered from a watcher on pattern, this.selectedMultiEpStyle or this.animeType
            // We want to make sure that the data passed on to the component is complete before making calls to the backend.
            // If we don't check on this, it will send api requests with null data.

            if (!pattern || this.animeType === null || this.selectedMultiEpStyle === null) {
                return;
            }

            // Update single
            this.testNaming(pattern, false, this.animeType).then(result => {
                this.namingExample = result + '.ext';
            });

            // Test naming
            this.checkNaming(pattern, false, this.animeType);

            if (this.isMulti) {
                this.testNaming(pattern, this.selectedMultiEpStyle, this.animeType).then(result => {
                    this.namingExampleMulti = result + '.ext';
                });

                this.checkNaming(pattern, this.selectedMultiEpStyle, this.animeType);
            }

            this.update();
        },
        update() {
            if (!this.flagLoaded) {
                return;
            }

            this.$emit('change', {
                pattern: this.isCustom ? this.customName : this.pattern,
                type: this.type,
                multiEpStyle: this.selectedMultiEpStyle,
                custom: this.isCustom,
                enabled: this.isEnabled,
                animeNamingType: Number(this.animeType)
            });
        },
        checkNaming(pattern, selectedMultiEpStyle, animeType) {
            if (!pattern) {
                return;
            }

            const params = {
                pattern,
                anime_type: animeType // eslint-disable-line camelcase
            };

            if (selectedMultiEpStyle) {
                params.multi = selectedMultiEpStyle;
            }

            const { $el } = this;
            const el = $($el);

            apiRoute.get('config/postProcessing/isNamingValid', { params, timeout: 20000 }).then(result => {
                if (result.data === 'invalid') {
                    el.find('#naming_pattern').qtip('option', {
                        'content.text': 'This pattern is invalid.',
                        'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                    });
                    el.find('#naming_pattern').qtip('toggle', true);
                    el.find('#naming_pattern').css('background-color', '#FFDDDD');
                } else if (result.data === 'seasonfolders') {
                    el.find('#naming_pattern').qtip('option', {
                        'content.text': 'This pattern would be invalid without the folders, using it will force "Flatten" off for all shows.',
                        'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                    });
                    el.find('#naming_pattern').qtip('toggle', true);
                    el.find('#naming_pattern').css('background-color', '#FFFFDD');
                } else {
                    el.find('#naming_pattern').qtip('option', {
                        'content.text': 'This pattern is valid.',
                        'style.classes': 'qtip-rounded qtip-shadow qtip-green'
                    });
                    el.find('#naming_pattern').qtip('toggle', false);
                    el.find('#naming_pattern').css('background-color', '#FFFFFF');
                }
            }).catch(error => {
                console.warn(error);
            });
        },
        updateCustomName() {
            // Store the custom naming pattern.
            if (!this.presetsPatterns.includes(this.pattern)) {
                this.customName = this.pattern;
            }

            // If the custom name is empty, let's use the last selected pattern.
            // We'd prefer to cache the last configured custom pattern.
            if (!this.customName) {
                this.customName = this.lastSelectedPattern;
            }
        }
    },
    computed: {
        isCustom() {
            if (this.pattern) {
                return !this.presetsPatterns.includes(this.pattern) || this.pattern === 'Custom...';
            }
            return false;
        },
        selectedNamingPattern: {
            get() {
                const filterPattern = () => {
                    const foundPattern = this.presets.filter(preset => preset.pattern === this.pattern);
                    if (foundPattern.length > 0) {
                        return foundPattern[0].example;
                    }
                    return false;
                };
                return this.isCustom ? 'Custom...' : filterPattern();
            },
            set(example) {
                // We need to convert the selected example back to a pattern
                this.pattern = this.presets.find(preset => preset.example === example).pattern;
            }
        },
        presetsPatterns() {
            return this.presets.map(preset => preset.pattern);
        },
        isMulti() {
            return Boolean(this.multiEpStyle);
        }
    },
    mounted() {
        this.pattern = this.namingPattern;

        // Add Custom... as an option to the presets.
        this.presets = this.namingPresets.concat({ pattern: 'Custom...', example: 'Custom...' });

        // Update the custom name
        this.updateCustomName();

        // Pass properties into local variables
        this.availableMultiEpStyles = this.multiEpStyles;
        this.selectedMultiEpStyle = this.multiEpStyle;
        this.animeType = this.animeNamingType;

        // If type is falsy, we asume it's the default name pattern. And thus enabled by default.
        this.isEnabled = this.type ? false : this.enabled;

        // Update the pattern samples
        this.updatePatternSamples();
    },
    watch: {
        // Update local variables when properties are updated
        enabled() {
            this.isEnabled = this.enabled;
        },
        namingPattern(newPattern, oldPattern) {
            this.lastSelectedPattern = newPattern || oldPattern;

            this.pattern = this.namingPattern;
            this.updateCustomName();
            this.updatePatternSamples();
        },
        namingPresets() {
            this.presets = this.namingPresets;
        },
        multiEpStyle() {
            this.selectedMultiEpStyle = this.multiEpStyle;
            this.updatePatternSamples();
        },
        multiEpStyles() {
            this.availableMultiEpStyles = this.multiEpStyles;
        },
        animeNamingType() {
            this.animeType = this.animeNamingType;
            this.updatePatternSamples();
        },
        type() {
            this.isEnabled = this.type ? false : this.enabled;
        }
    }
};
</script>
<style>

</style>
