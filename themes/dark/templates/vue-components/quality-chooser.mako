<script type="text/x-template" id="quality-chooser-template">
    <div id="quality_chooser_wrapper">
        <select v-model.number="selectedQualityPreset" name="quality_preset" class="form-control form-control-inline input-sm">
            <option :value.number="0">Custom</option>
            <option v-for="preset in qualityPresets" :value.number="preset" :selected="overallQuality === preset" :style="qualityPresetStrings[preset].endsWith('0p') ? 'padding-left: 15px;' : ''">{{qualityPresetStrings[preset]}}</option>
        </select>
        <div id="customQualityWrapper">
            <div style="padding-left: 0;" v-if="selectedQualityPreset === 0">
                <p><b><strong>Preferred</strong></b> qualities will replace those in <b><strong>allowed</strong></b>, even if they are lower.</p>
                <div style="padding-right: 40px; text-align: left; float: left;">
                    <h5>Allowed</h5>
                    <select v-model="selectedAllowed" name="allowed_qualities" multiple="multiple" :size="allowedQualityList.length" class="form-control form-control-inline input-sm">
                        <option v-for="quality in allowedQualityList" :selected="quality in allowedQualities" :value="quality">{{qualityStrings[quality]}}</option>
                    </select>
                </div>
                <div style="text-align: left; float: left;">
                    <h5>Preferred</h5>
                    <select v-model="selectedPreferred" name="preferred_qualities" multiple="multiple" :size="preferredQualityList.length" class="form-control form-control-inline input-sm">
                        <option v-for="quality in preferredQualityList" :selected="quality in preferredQualities" :value="quality">{{qualityStrings[quality]}}</option>
                    </select>
                </div>
            </div>
            <div style="clear:both;"></div>
            <div v-if="(selectedAllowed.length + selectedPreferred.length) >= 1" id="qualityExplanation">
                <h5><b>Quality setting explanation:</b></h5>
                <h5 v-if="selectedPreferred.length === 0">This will download <b>any</b> of these qualities and then stops searching: <label id="allowedExplanation">{{allowedExplanation.join(', ')}}</label></h5>
                <template v-else>
                <h5>Downloads <b>any</b> of these qualities: <label id="allowedPreferredExplanation">{{allowedExplanation.join(', ')}}</label></h5>
                <h5>But it will stop searching when one of these is downloaded:  <label id="preferredExplanation">{{preferredExplanation.join(', ')}}</label></h5>
                </template>
            </div>
            <div v-else>Please select at least one allowed quality.</div>
            <div v-if="seriesSlug && (selectedAllowed.length + selectedPreferred.length) >= 1">
                <h5 class="red-text" id="backloggedEpisodes" v-html="backloggedEpisodes"></h5>
            </div>
            <div id="archive" v-if="archive">
                <h5>
                    <b>Archive downloaded episodes that are not currently in <a target="_blank" href="manage/backlogOverview/" style="color: blue;">backlog</a>.</b>
                    <br />Avoids unnecessarily increasing your backlog
                    <br />
                </h5>
                <button @click="archiveEpisodes" id="archiveEpisodes" class="btn btn-inline">Archive episodes</button>
                <h5>{{archivedStatus}}</h5>
            </div>
        </div>
    </div>
</script>
<%!
    import json
    from medusa import app
    from medusa.numdict import NumDict
    from medusa.common import Quality, qualityPresets, qualityPresetStrings
%>
<%
if not show is UNDEFINED:
    __quality = int(show.quality)
else:
    __quality = int(app.QUALITY_DEFAULT)
allowed_qualities, preferred_qualities = Quality.split_quality(__quality)
overall_quality = Quality.combine_qualities(allowed_qualities, preferred_qualities)
selected = None
%>
<%
def convert(obj):
    ## This converts the keys to strings as keys can't be ints
    if isinstance(obj, (NumDict, dict)):
        new_obj = {}
        for key in obj:
            new_obj[str(key)] = obj[key]
        obj = new_obj

    return json.dumps(obj)

%>
<script>
Vue.component('quality-chooser', {
    name: 'quality-chooser',
    template: '#quality-chooser-template',
    data() {
        return {
            // Python convertions
            allowedQualities: ${convert(allowed_qualities)},
            preferredQualities: ${convert(preferred_qualities)},
            overallQuality: ${overall_quality},
            qualityStrings: ${convert(Quality.qualityStrings)},
            qualityPresets: ${convert(qualityPresets)},
            qualityPresetStrings: ${convert(qualityPresetStrings)},
            selectedQualityPreset: ${convert(overall_quality) if overall_quality in qualityPresets else '0'},

            // JS only
            seriesSlug: $('#series-slug').attr('value'), // This should be moved to medusa-lib
            customQuality: false, // Not sure what this should be set as by default since we shsould be using the current show quality
            archive: false,
            archivedStatus: '',
            selectedAllowed: [],
            selectedPreferred: []
        };
    },
    computed: {
        allowedExplanation() {
            const allowed = this.selectedAllowed;
            return allowed.map(quality => this.qualityStrings[quality])
        },
        preferredExplanation() {
            const preferred = this.selectedPreferred;
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

            const selectedAllowed = this.selectedAllowed;
            const selectedPreferred = this.selectedPreferred;
            // @TODO: $('#series-slug').attr('value') needs to be replaced with this.series.slug
            const url = 'series/' + this.seriesSlug +
                      '/legacy/backlogged' +
                      '?allowed=' + selectedAllowed +
                      '&preferred=' + selectedPreferred;
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
                // Recalculate backlogged episodes after we archive it
                this.$forceUpdate();
            } else if (response.status === 204) {
                this.archivedStatus = 'No episodes to be archived';
            }
            // Restore button text
            // @TODO: Replace these with vue
            $('#archiveEpisodes').text('Finished');
            $('#archiveEpisodes').prop('disabled', true);
        },
        setQualityFromPreset(preset, oldPreset) {
            // If empty skip
            if (preset === undefined || preset === null) return;

            this.customQuality = parseInt(preset, 10) === 0 || !(this.qualityPresets.includes(preset));

            // If custom set to last preset
            if (this.customQuality) preset = oldPreset;

            this.selectedAllowed = Object.keys(this.qualityStrings)
                .filter(quality => (preset & quality) > 0);
            this.selectedPreferred = Object.keys(this.qualityStrings)
                .filter(quality => (preset & (quality << 16)) > 0);
        }
    },
    watch: {
        selectedQualityPreset(preset, oldPreset) {
            this.setQualityFromPreset(preset, oldPreset);
        }
    }
});
</script>
