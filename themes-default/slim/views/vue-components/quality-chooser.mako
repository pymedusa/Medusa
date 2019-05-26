<script type="text/x-template" id="quality-chooser-template">
    <div id="quality_chooser_wrapper">
        <select v-model.number="selectedQualityPreset" name="quality_preset" class="form-control form-control-inline input-sm">
            <option v-if="keep" value="keep">&lt; Keep &gt;</option>
            <option :value="0">Custom</option>
            <option v-for="preset in qualityPresets" :value="preset" :style="qualityPresetStrings[preset].endsWith('0p') ? 'padding-left: 15px;' : ''">{{qualityPresetStrings[preset]}}</option>
        </select>
        <div id="customQualityWrapper">
            <div style="padding-left: 0;" v-show="selectedQualityPreset === 0">
                <p><b><strong>Preferred</strong></b> qualities will replace those in <b><strong>allowed</strong></b>, even if they are lower.</p>
                <div style="padding-right: 40px; text-align: left; float: left;">
                    <h5>Allowed</h5>
                    <select v-model.number="allowedQualities" name="allowed_qualities" multiple="multiple" :size="validQualities.length" class="form-control form-control-inline input-sm">
                        <option v-for="quality in validQualities" :value="quality">{{qualityStrings[quality]}}</option>
                    </select>
                </div>
                <div style="text-align: left; float: left;">
                    <h5>Preferred</h5>
                    <select v-model.number="preferredQualities" name="preferred_qualities" multiple="multiple" :size="validQualities.length" class="form-control form-control-inline input-sm" :disabled="allowedQualities.length === 0">
                        <option v-for="quality in validQualities" :value="quality">{{qualityStrings[quality]}}</option>
                    </select>
                </div>
            </div>
            <div style="clear:both;"></div>
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
                <h5 class="{ 'red-text': !backloggedEpisodes.status }" v-html="backloggedEpisodes.html"></h5>
            </div>
            <div v-if="archive" id="archive">
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
const QualityChooserComponent = {
    name: 'quality-chooser',
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
            validator: value => ['keep', 'show'].includes(value)
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
            lock: false, // FIXME: Remove this hack, see `watch.overallQuality` below
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
            return allowed.map(quality => this.qualityStrings[quality]);
        },
        preferredExplanation() {
            const preferred = this.preferredQualities;
            return preferred.map(quality => this.qualityStrings[quality]);
        },
        allowedPreferredExplanation() {
            const allowed = this.allowedExplanation;
            const preferred = this.preferredExplanation;
            return allowed.concat(
                preferred.filter(item => !allowed.includes(item))
            );
        },
        validQualities() {
            return Object.keys(this.qualityStrings)
                .filter(val => val > ${Quality.NA});
        }
    },
    asyncComputed: {
        async backloggedEpisodes() {
            const { seriesSlug, allowedQualities, preferredQualities } = this;

            // Skip if no seriesSlug as that means were on a addShow page
            if (!seriesSlug) return {};

            // Skip if no qualities are selected
            if (allowedQualities.length === 0 && preferredQualities.length === 0) return {};

            // @TODO: $('#series-slug').attr('value') needs to be replaced with this.series.slug
            const url = 'series/' + seriesSlug +
                        '/legacy/backlogged' +
                        '?allowed=' + allowedQualities.join(',') +
                        '&preferred=' + preferredQualities.join(',');
            let status = false; // Set to `false` for red text, `true` for normal color
            let response;
            try {
                response = await api.get(url);
            } catch (error) {
                return {
                    status,
                    html: '<b>Failed to get backlog prediction</b><br />' + String(error)
                };
            }
            const newBacklogged = response.data.new;
            const existingBacklogged = response.data.existing;
            const variation = Math.abs(newBacklogged - existingBacklogged);
            let html = 'Current backlog: <b>' + existingBacklogged + '</b> episodes<br>';
            if (newBacklogged === -1 || existingBacklogged === -1) {
                html = 'No qualities selected';
            } else if (newBacklogged === existingBacklogged) {
                html += 'This change won\'t affect your backlogged episodes';
                status = true;
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

            return {
                status,
                html
            };
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
                // Recalculate backlogged episodes after we archive it
                this.$asyncComputed.backloggedEpisodes.update();
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

            // If preset is custom, set to last preset
            if (parseInt(preset, 10) === 0 || !this.qualityPresets.includes(preset)) {
                // [Mass Edit] If changing from `keep`, restore the original value
                preset = oldPreset === 'keep' ? this.overallQuality : oldPreset;
            }

            // Convert values to unsigned int, and filter selected/preferred qualities
            const reducer = (results, quality) => {
                quality = parseInt(quality, 10);
                // Allowed
                if (( (preset & quality) >>> 0 ) > 0) {
                    results[0].push(quality);
                }
                // Preferred
                if (( (preset & (quality << 16)) >>> 0 ) > 0) {
                    results[1].push(quality);
                }
                return results;
            };
            const qualities = Object.keys(this.qualityStrings).reduce(reducer, [[], []]);
            this.allowedQualities = qualities[0];
            this.preferredQualities = qualities[1];
        }
    },
    watch: {
        /*
        FIXME: Remove this watch and the `this.lock` hack.
        This is causing the preset selector to change from `Custom` to a preset,
        when the correct qualities for that preset are selected.
        */
        overallQuality(newValue) {
            if (this.lock) {
                return;
            }
            const { qualityPresets, keep, setQualityFromPreset } = this;
            this.selectedQualityPreset = keep === 'keep' ? 'keep' : (qualityPresets.includes(newValue) ? newValue : 0);
            setQualityFromPreset(this.selectedQualityPreset, newValue);
        },
        selectedQualityPreset(preset, oldPreset) {
            this.setQualityFromPreset(preset, oldPreset);
        },
        allowedQualities(newQuality, oldQuality) {
            this.lock = true; // FIXME: Remove this hack, see above
            this.$emit('update:quality:allowed', newQuality);
            // FIXME: Remove this hack, see above
            this.$nextTick(() => {
                this.lock = false;
            });
        },
        preferredQualities(newQuality, oldQuality) {
            this.lock = true; // FIXME: Remove this hack, see above
            this.$emit('update:quality:preferred', newQuality);
            // FIXME: Remove this hack, see above
            this.$nextTick(() => {
                this.lock = false;
            });
        }
    }
};

window.components.push(QualityChooserComponent);
</script>
