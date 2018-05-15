<script type="text/x-template" id="quality-chooser-template">
    <div id="quality_chooser_wrapper">
        <select v-model.number="selectedQualityPreset" name="quality_preset" class="form-control form-control-inline input-sm">
            <option value="keep" v-if="keep">&lt; Keep &gt;</option>
            <option :value.number="0">Custom</option>
            <option v-for="preset in qualityPresets" :value.number="preset" :style="qualityPresetStrings[preset].endsWith('0p') ? 'padding-left: 15px;' : ''">{{qualityPresetStrings[preset]}}</option>
        </select>
        <div id="customQualityWrapper">
            <div style="padding-left: 0;" v-show="selectedQualityPreset === 0">
                <p><b><strong>Preferred</strong></b> qualities will replace those in <b><strong>allowed</strong></b>, even if they are lower.</p>
                <div style="padding-right: 40px; text-align: left; float: left;">
                    <h5>Allowed</h5>
                    <select v-model="allowedQualities" name="allowed_qualities" multiple="multiple" :size="allowedQualityList.length" class="form-control form-control-inline input-sm">
                        <option v-for="quality in allowedQualityList" :value="quality">{{qualityStrings[quality]}}</option>
                    </select>
                </div>
                <div style="text-align: left; float: left;">
                    <h5>Preferred</h5>
                    <select v-model="preferredQualities" name="preferred_qualities" multiple="multiple" :size="preferredQualityList.length" class="form-control form-control-inline input-sm">
                        <option v-for="quality in preferredQualityList" :value="quality">{{qualityStrings[quality]}}</option>
                    </select>
                </div>
            </div>
            <div style="clear:both;"></div>
            ## @TODO: This needs cleaning up. Vue v2.1.0 introduces `v-else-if` which might be useful in this case
            <div v-if="selectedQualityPreset !== 'keep'">
                <div v-if="(allowedQualities.length + preferredQualities.length) >= 1" id="qualityExplanation">
                    <h5><b>Quality setting explanation:</b></h5>
                    <h5 v-if="preferredQualities.length === 0">This will download <b>any</b> of these qualities and then stops searching: <label id="allowedExplanation">{{allowedExplanation.join(', ')}}</label></h5>
                    <template v-else>
                    <h5>Downloads <b>any</b> of these qualities: <label id="allowedPreferredExplanation">{{allowedExplanation.join(', ')}}</label></h5>
                    <h5>But it will stop searching when one of these is downloaded:  <label id="preferredExplanation">{{preferredExplanation.join(', ')}}</label></h5>
                    </template>
                </div>
                <div v-else>Please select at least one allowed quality.</div>
            </div>
            <div v-if="seriesSlug && (allowedQualities.length + preferredQualities.length) >= 1">
                <h5 class="red-text" id="backloggedEpisodes" v-html="backloggedEpisodes"></h5>
            </div>
            <div id="archive" v-if="archive">
                <h5>
                    <b>Archive downloaded episodes that are not currently in
                    <a target="_blank" href="manage/backlogOverview/" style="color: blue; text-decoration: underline;">backlog</a>.</b>
                    <br />Avoids unnecessarily increasing your backlog
                    <br />
                </h5>
                <button @click.prevent="archiveEpisodes" :disabled="archiveButton.disabled" class="btn-medusa btn-inline">{{archiveButton.text}}</button>
                <h5>{{archivedStatus}}</h5>
            </div>
        </div>
    </div>
</script>
<%!
    import json
    from medusa import app
    from medusa.common import Quality, qualityPresets, qualityPresetStrings
%>
<%
if show is not UNDEFINED:
    __quality = int(show.quality)
else:
    __quality = int(app.QUALITY_DEFAULT)
allowed_qualities, preferred_qualities = Quality.split_quality(__quality)
overall_quality = Quality.combine_qualities(allowed_qualities, preferred_qualities)

def convert(obj):
    ## This converts the keys to strings as keys can't be ints
    if isinstance(obj, dict):
        new_obj = {}
        for key in obj:
            new_obj[str(key)] = obj[key]
        obj = new_obj

    return json.dumps(obj)
%>
<script>
Vue.component('quality-chooser', {
    template: '#quality-chooser-template',
    props: {
        overallQuality: {
            type: Number,
            // Python conversion
            default: ${overall_quality}
        },
        keep: {
            type: String,
            default: null,
            validator(value) {
                return ['keep', 'show'].includes(value);
            }
        }
    },
    data() {
        // Python conversions
        const qualityPresets = ${convert(qualityPresets)};
        return {
            qualityStrings: ${convert(Quality.qualityStrings)},
            qualityPresets,
            qualityPresetStrings: ${convert(qualityPresetStrings)},

            // JS only
            lock: false,
            allowedQualities: [],
            preferredQualities: [],
            seriesSlug: $('#series-slug').attr('value'), // This should be moved to medusa-lib
            selectedQualityPreset: this.keep === 'keep' ? 'keep' : (qualityPresets.includes(this.overallQuality) ? this.overallQuality : 0),
            archive: false,
            archivedStatus: '',
            archiveButton: {
                text: 'Archive episodes',
                disabled: false
            }
        };
    },
    computed: {
        allowedExplanation() {
            const allowed = this.allowedQualities;
            return allowed.map(quality => this.qualityStrings[quality])
        },
        preferredExplanation() {
            const preferred = this.preferredQualities;
            return preferred.map(quality => this.qualityStrings[quality])
        },
        allowedPreferredExplanation() {
            const allowed = this.allowedExplanation;
            const preferred = this.preferredExplanation;
            return allowed.concat(preferred.filter(item => allowed.indexOf(item) < 0))
        },
        allowedQualityList() {
            return Object.keys(this.qualityStrings)
                .filter(val => val > ${Quality.NONE});
        },
        preferredQualityList() {
            return Object.keys(this.qualityStrings)
                .filter(val => val > ${Quality.NONE} && val < ${Quality.UNKNOWN});
        }
    },
    asyncComputed: {
        async backloggedEpisodes() {
            // Skip if no seriesSlug as that means were on a addShow page
            if (!this.seriesSlug) return;

            const allowedQualities = this.allowedQualities;
            const preferredQualities = this.preferredQualities;

            // Skip if no qualities are selected
            if (!allowedQualities.length && !preferredQualities.length) return;

            // @TODO: $('#series-slug').attr('value') needs to be replaced with this.series.slug
            const url = 'series/' + this.seriesSlug +
                        '/legacy/backlogged' +
                        '?allowed=' + allowedQualities +
                        '&preferred=' + preferredQualities;
            const response = await api.get(url);
            const newBacklogged = response.data.new;
            const existingBacklogged = response.data.existing;
            const variation = Math.abs(newBacklogged - existingBacklogged);
            let html = 'Current backlog: <b>' + existingBacklogged + '</b> episodes<br>';
            if (newBacklogged === -1 || existingBacklogged === -1) {
                html = 'No qualities selected';
            } else if (newBacklogged === existingBacklogged) {
                html += 'This change won\'t affect your backlogged episodes';
            } else {
                html += '<br />New backlog: <b>' + newBacklogged + '</b> episodes';
                html += '<br /><br />';
                let change = '';
                if (newBacklogged > existingBacklogged) {
                    html += '<b>WARNING</b>: ';
                    change = 'increase';
                    // Only show the archive action div if we have backlog increase
                    this.archive = true;
                } else {
                    change = 'decrease';
                }
                html += 'Backlog will ' + change + ' by <b>' + variation + '</b> episodes.';
            }

            return html;
        }
    },
    mounted() {
        this.setQualityFromPreset(this.selectedQualityPreset, this.overallQuality);
    },
    methods: {
        async archiveEpisodes() {
            this.archivedStatus = 'Archiving...';

            const url = 'series/' + this.seriesSlug + '/operation';
            const response = await api.post(url, { type: 'ARCHIVE_EPISODES' });

            if (response.status === 201) {
                this.archivedStatus = 'Successfully archived episodes';
                // @FIXME: This does nothing.
                // Recalculate backlogged episodes after we archive it
                // this.$forceUpdate();
            } else if (response.status === 204) {
                this.archivedStatus = 'No episodes to be archived';
            }
            // Restore button text
            this.archiveButton.text = 'Finished';
            this.archiveButton.disabled = true;
        },
        setQualityFromPreset(preset, oldPreset) {
            // If empty skip
            if (preset === undefined || preset === null) return;

            // If preset is custom set to last preset
            if (parseInt(preset, 10) === 0 || !(this.qualityPresets.includes(preset))) preset = oldPreset;

            // Convert values to int, and filter selected/prefrred qualities
            this.allowedQualities = Object.keys(this.qualityStrings)
                .map(quality => parseInt(quality, 10))
                .filter(quality => (preset & quality) > 0);
            this.preferredQualities = Object.keys(this.qualityStrings)
                .map(quality => parseInt(quality, 10))
                .filter(quality => (preset & (quality << 16)) > 0);
        }
    },
    watch: {
        /**
         * overallQuality property might receive values originating from the API,
         * that are sometimes not avaiable when rendering.
         * @TODO: Maybe we can remove this in the future.
         */
        overallQuality(newValue, oldValue) {
            this.lock = true;
            this.selectedQualityPreset = this.keep === 'keep' ? 'keep' : (this.qualityPresets.includes(newValue) ? newValue : 0),
            this.setQualityFromPreset(this.selectedQualityPreset, newValue);
            this.$nextTick(() => this.lock = false);
        },
        selectedQualityPreset(preset, oldPreset) {
            this.setQualityFromPreset(preset, oldPreset);
        },
        allowedQualities(newQuality, oldQuality) {
            if (!this.lock) {
                this.$emit('update:quality:allowed', this.allowedQualities.map(quality => parseInt(quality, 10)));
            }
        },
        preferredQualities(newQuality, oldQuality) {
            if (!this.lock) {
                this.$emit('update:quality:preferred', this.preferredQualities.map(quality => parseInt(quality, 10)));
            }
        }
    }
});
</script>
