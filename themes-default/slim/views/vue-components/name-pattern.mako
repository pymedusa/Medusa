<script type="text/x-template" id="name-pattern-tempate">
    <div id="name_pattern_wrapper">

        <div v-if="namingCustom" class="field-pair">
            <input type="checkbox" class="enabler" id="enable_naming_custom" name="enable_naming_custom" v-model="isEnabled"/>
            <label for="enable_naming_custom">
                <span class="component-title">Custom {{ namingCustom }}</span>
                <span class="component-desc">Name {{ namingCustom }} shows differently than regular shows?</span>
            </label>
        </div>

        <div v-if="!namingCustom || isEnabled" class="episode-naming">
                <div class="field-pair">
                        <label class="nocheck" for="name_presets">
                            <span class="component-title">Name Pattern:</span>
                            <span class="component-desc">
                                <select id="name_presets" class="form-control input-sm" v-model="selectedNamingPattern" @change="updatePatternSamples">
                                    <option id="preset" v-for="preset in namingPresets">{{ preset }}</option>
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
                    <div id="naming_example_multi_div">
                        <h3>Multi-EP sample:</h3>
                        <div class="example">
                            <span class="jumbo" id="naming_example_multi">{{ namingExampleMulti }}</span>
                        </div>
                        <br>
                    </div>
            
                    <!-- Anime only -->
                    <div v-if="animeNamingType > 0" class="field-pair">
                        <input type="radio" name="naming_anime" id="naming_anime" value="1" v-model="animeNamingType" />
                        <label for="naming_anime">
                            <span class="component-title">Add Absolute Number</span>
                            <span class="component-desc">Add the absolute number to the season/episode format?</span>
                        </label>
                        <label class="nocheck">
                            <span class="component-title">&nbsp;</span>
                            <span class="component-desc">Only applies to animes. (eg. S15E45 - 310 vs S15E45)</span>
                        </label>
                    </div>
                    <div v-if="animeNamingType > 0" class="field-pair">
                        <input type="radio" name="naming_anime" id="naming_anime_only" value="2" v-model="animeNamingType"/>
                        <label for="naming_anime_only">
                            <span class="component-title">Only Absolute Number</span>
                            <span class="component-desc">Replace season/episode format with absolute number</span>
                        </label>
                        <label class="nocheck">
                            <span class="component-title">&nbsp;</span>
                            <span class="component-desc">Only applies to animes.</span>
                        </label>
                    </div>
                    <div v-if="animeNamingType > 0"  class="field-pair">
                        <input type="radio" name="naming_anime" id="naming_anime_none" value="3" v-model="animeNamingType"/>
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
            pattern: {
                type: String,
                default: ''
            },
            presets: {
                type: Array,
                default: []
            },
            animeType: {
                type: Number,
                default: 0
            },
            /**
             * Provide the custom naming type. -Like sports, anime, air by date- description.
             * If none provided we asume this is the default episode naming component.
             * And that means there will be no checkbox available to enable/disable it.
             */
            namingCustom: {
                type: String,
                default: ''
            },
            enabledNamingCustom: {
                type: Boolean,
                default: false
            }
        },
        data() {
            return {
                namingPattern: '',
                customName: '',
                namingPresets: [],
                showLegend: false,
                namingExample: '',
                namingExampleMulti: '',
                animeNamingType: this.animeType,
                isEnabled: this.enabledNamingCustom,
                isMulti: true
            }
        },
        methods: {
            getDateFormat(format) {
                return dateFns.format(new Date(), format);
            },
            async testNaming(pattern, isMulti, animeType) {
                console.debug('Test pattern ' + pattern + ' for ' + (isMulti) ? 'multi' : 'single' + ' ep');
                const params = {
                    pattern: pattern,
                    anime_type: animeType
                }

                if (isMulti) {
                    params.multi = (isMulti) ? 1 : 0 
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
                const namingPattern = (this.isCustom) ? this.customName : this.namingPattern; 
                
                // Update single
                this.namingExample = await this.testNaming(namingPattern, false, this.animeNamingType) + '.ext';
                console.debug('Result of naming pattern check: ' + this.namingExample);
                
                // Update multi if needed
                if (this.isMulti) {
                    this.namingExampleMulti = await this.testNaming(namingPattern, this.isMulti, this.animeNamingType) + '.ext';
                }
            }
        },
        computed: {
            isCustom() {
                return !this.namingPresets.includes(this.namingPattern) || this.namingPattern === 'Custom...';
            },
            selectedNamingPattern: {
                get: function() {
                    return (this.isCustom) ? 'Custom...' : this.namingPattern;
                },
                set: function(value) {
                    this.namingPattern = value;
                }
            }
        },
        mounted() {
            this.namingPattern = this.pattern;

            // Store the custom naming pattern.
            if (!this.presets.includes(this.namingPattern)) {
                this.customName = this.namingPattern;
            }

            // Add Custom... as an option to the namingPresets.
            this.namingPresets = this.presets.concat('Custom...');

            // Update the pattern samples
            this.updatePatternSamples();

        },
        watch: {
            customName(newValue, oldValue) {
                this.$emit('update:custom', {
                    pattern: (this.isCustom) ? newValue : this.namingPattern
                });
            },
            namingPattern(newValue, oldValue) {
                this.$emit('update:custom', {
                    pattern: (this.isCustom) ? this.customName : this.namingPattern
                });
            }
        }
    
    });
    </script>