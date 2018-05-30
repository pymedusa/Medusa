<script type="text/x-template" id="name-pattern-tempate">
    <div id="name_pattern_wrapper">

        <!-- If a 'type' is passed, it means that where checking a custom naming pattern. As for example sports, air-by-date etc.
        In that case, we're showing this checkbox, to display the rest of the form.
        If type evaulates to an empty string, we're asuming this is the default name pattern. And it's enabled by default. -->
        <div v-if="type" class="field-pair">
            <input type="checkbox" class="enabler" id="enable_naming_custom" name="enable_naming_custom" v-model="isEnabled"/>
            <label for="enable_naming_custom">
                <span class="component-title">Custom {{ type }}</span>
                <span class="component-desc">Name {{ type }} shows differently than regular shows?</span>
            </label>
        </div>

        <div v-if="!type || isEnabled" class="episode-naming">
            <div class="field-pair">
                <label class="nocheck" for="name_presets">
                    <span class="component-title">Name Pattern:</span>
                    <span class="component-desc">
                        <select id="name_presets" class="form-control input-sm" v-model="selectedNamingPattern" @change="updatePatternSamples">
                            <option id="preset" v-for="preset in presets">{{ preset }}</option>
                        </select>
                    </span>
                </label>
            </div>
                    
            <div id="naming_custom">
                <div class="field-pair" style="padding-top: 0;">
                    <label class="nocheck">
                        <span class="component-title">
                            &nbsp;
                        </span>
                        <span class="component-desc">
                            <input v-if="isCustom" type="text" name="naming_pattern" id="naming_pattern" v-model="customName" @change="updatePatternSamples" class="form-control input-sm input350"/>
                            <img src="images/legend16.png" width="16" height="16" alt="[Toggle Key]" id="show_naming_key" title="Toggle Naming Legend" class="legend" @click="showLegend = !showLegend" />
                        </span>
                    </label>
                </div>

                <div v-if="selectedMultiEpStyle" class="field-pair">
                    <label class="nocheck" for="naming_multi_ep">
                        <span class="component-title">Multi-Episode Style:</span>
                        <span class="component-desc">
                            <select id="naming_multi_ep" name="naming_multi_ep" v-model="selectedMultiEpStyle" class="form-control input-sm" @change="updatePatternSamples">
                                <option id="multiEpStyle" :value="multiEpStyle.value" v-for="multiEpStyle in availableMultiEpStyles">{{ multiEpStyle.text }}</option>
                            </select>
                        </span>
                    </label>
                </div>
        
                <div id="naming_key" class="nocheck" v-if="showLegend">
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
                                <td>{{ getDateFormat('D')}}</td>
                            </tr>
                            <tr>
                                <td>&nbsp;</td>
                                <td>%Y</td>
                                <td>{{ getDateFormat('YY')}}</td>
                            </tr>
                            <tr>
                                <td class="align-right"><b>Post-Processing Date:</b></td>
                                <td>%CM</td>
                                <td>{{ getDateFormat('M') }}</td>
                            </tr>
                            <tr class="even">
                                <td>&nbsp;</td>
                                <td>%CD</td>
                                <td>{{ getDateFormat('D')}}</td>
                            </tr>
                            <tr>
                                <td>&nbsp;</td>
                                <td>%CY</td>
                                <td>{{ getDateFormat('YY')}}</td>
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
                                <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="Multi-EP style is ignored"></i> <b>Release Name:</b></td>
                                <td>%RN</td>
                                <td>Show.Name.S02E03.HDTV.x264-RLSGROUP</td>
                            </tr>
                            <tr>
                                <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="UNKNOWN_RELEASE_GROUP is used in place of RLSGROUP if it could not be properly detected"></i> <b>Release Group:</b></td>
                                <td>%RG</td>
                                <td>RLSGROUP</td>
                            </tr>
                            <tr class="even">
                                <td class="align-right"><i class="glyphicon glyphicon-info-sign" title="If episode is proper/repack add 'proper' to name."></i> <b>Release Type:</b></td>
                                <td>%RT</td>
                                <td>PROPER</td>
                            </tr>
                        </tbody>
                        </table>
                        <br>
                    </div>
                </div>
                        
                <div id="naming_example_div">
                    <h3>Single-EP Sample:</h3>
                    <div class="example">
                        <span class="jumbo" id="naming_example">{{ namingExample }}</span>
                    </div>
                    <br>
                </div>
                <div v-if="isMulti" id="naming_example_multi_div">
                    <h3>Multi-EP sample:</h3>
                    <div class="example">
                        <span class="jumbo" id="naming_example_multi">{{ namingExampleMulti }}</span>
                    </div>
                    <br>
                </div>
        
                <!-- Anime only -->
                <div v-if="animeType > 0" class="field-pair">
                    <input type="radio" name="naming_anime" id="naming_anime" value="1" v-model="animeType" @change="updatePatternSamples"/>
                    <label for="naming_anime">
                        <span class="component-title">Add Absolute Number</span>
                        <span class="component-desc">Add the absolute number to the season/episode format?</span>
                    </label>
                    <label class="nocheck">
                        <span class="component-title">&nbsp;</span>
                        <span class="component-desc">Only applies to animes. (eg. S15E45 - 310 vs S15E45)</span>
                    </label>
                </div>
                <div v-if="animeType > 0" class="field-pair">
                    <input type="radio" name="naming_anime" id="naming_anime_only" value="2" v-model="animeType" @change="updatePatternSamples"/>
                    <label for="naming_anime_only">
                        <span class="component-title">Only Absolute Number</span>
                        <span class="component-desc">Replace season/episode format with absolute number</span>
                    </label>
                    <label class="nocheck">
                        <span class="component-title">&nbsp;</span>
                        <span class="component-desc">Only applies to animes.</span>
                    </label>
                </div>
                <div v-if="animeType > 0"  class="field-pair">
                    <input type="radio" name="naming_anime" id="naming_anime_none" value="3" v-model="animeType" @change="updatePatternSamples"/>
                    <label for="naming_anime_none">
                        <span class="component-title">No Absolute Number</span>
                        <span class="component-desc">Dont include the absolute number</span>
                    </label>
                    <label class="nocheck">
                        <span class="component-title">&nbsp;</span>
                        <span class="component-desc">Only applies to animes.</span>
                    </label>
                </div>
        </div>

    </div>

</script>


<script>
    Vue.component('name-pattern', {
        template: '#name-pattern-tempate',
        props: {
            namingPattern: {
                type: String,
                default: ''
            },
            namingPresets: {
                type: Array,
                default: () => []
            },
            /**
             * The selected multi ep style
             */
            multiEpStyle: {
                type: Number,
                default: null
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
            enabled: {
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
                isMulti: false,
                selectedMultiEpStyle: 1,
                animeType: 0
            }
        },
        methods: {
            getDateFormat(format) {
                return dateFns.format(new Date(), format);
            },
            async testNaming(pattern, selectedMultiEpStyle, animeType) {
                console.debug('Test pattern ' + pattern + ' for ' + (selectedMultiEpStyle) ? 'multi' : 'single' + ' ep');
                const params = {
                    pattern: pattern,
                    anime_type: animeType
                }

                if (selectedMultiEpStyle) {
                    params.multi = selectedMultiEpStyle;
                }

                try {
                    const result = await apiRoute.get('config/postProcessing/testNaming', {params: params});
                    return result.data;
                } catch (e) {
                    console.warning(e);
                }
            },
            async updatePatternSamples() {
                // If it's a custom pattern, we need to get the custom pattern from this.customName
                const pattern = this.isCustom ? this.customName : this.pattern; 
                
                // Update single
                this.namingExample = await this.testNaming(pattern, false, this.animeType) + '.ext';
                console.debug('Result of naming pattern check: ' + this.namingExample);
                
                // Update multi if needed
                if (this.isMulti) {
                    this.namingExampleMulti = await this.testNaming(pattern, this.selectedMultiEpStyle, this.animeType) + '.ext';
                }
            },
            update(newValue) {
                this.$emit('change', {
                    pattern: (this.isCustom) ? this.customName : this.pattern,
                    type: this.type,
                    multiEpStyle: this.selectedMultiEpStyle,
                    custom: this.isCustom,
                    enabled: this.isEnabled,
                    animeNamingType: this.animeType
                });
            }
        },
        computed: {
            isCustom() {
                return !this.presets.includes(this.pattern) || this.pattern === 'Custom...';
            },
            selectedNamingPattern: {
                get: function() {
                    return this.isCustom ? 'Custom...' : this.pattern;
                },
                set: function(value) {
                    this.pattern = value;
                }
            }
        },
        mounted() {
            this.pattern = this.namingPattern;

            // Store the custom naming pattern.
            if (!this.presets.includes(this.pattern)) {
                this.customName = this.pattern;
            }

            // Add Custom... as an option to the presets.
            this.presets = this.namingPresets.concat('Custom...');

            // Pass properties into local variables
            this.availableMultiEpStyles = this.multiEpStyles;
            this.selectedMultiEpStyle = this.multiEpStyle;
            this.animeType = this.animeNamingType;
            this.isMulti = Boolean(this.multiEpStyle)

            // If type is falsy, we asume it's the default name pattern. And thus enabled by default.
            this.isEnabled = this.type ? false : this.enabled;

            // Update the pattern samples
            this.updatePatternSamples();

        },
        watch: {
            customName(newValue) {
                this.update(newValue);
            },
            pattern() {
                this.update();
            },
            selectedMultiEpStyle() {
                this.update();
            },
            isEnabled() {
                this.update();
            },
            animeType() {
                this.update();
            }
        }
    
    });
    </script>