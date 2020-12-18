<template>
    <div>
        <select
            v-model.number="selectedQualityPreset"
            name="quality_preset"
            class="form-control form-control-inline input-sm"
        >
            <option v-if="keep" value="keep">&lt; Keep &gt;</option>
            <option :value="0">Custom</option>
            <option
                v-for="preset in qualityPresets"
                :key="`quality-preset-${preset.key}`"
                :value="preset.value"
            >
                {{ preset.name }}
            </option>
        </select>

        <div v-show="selectedQualityPreset === 0" id="customQualityWrapper">
            <p>
                <b><strong>Preferred</strong></b> qualities will replace those in <b><strong>allowed</strong></b>, even if they are lower.
            </p>
            <div>
                <h5>Allowed</h5>
                <select
                    v-model.number="allowedQualities"
                    name="allowed_qualities"
                    multiple="multiple"
                    :size="validQualities.length"
                    class="form-control form-control-inline input-sm"
                >
                    <option
                        v-for="quality in validQualities"
                        :key="`quality-list-${quality.key}`"
                        :value="quality.value"
                    >
                        {{ quality.name }}
                    </option>
                </select>
            </div>
            <div>
                <h5>Preferred</h5>
                <select
                    v-model.number="preferredQualities"
                    name="preferred_qualities"
                    multiple="multiple"
                    :size="validQualities.length"
                    class="form-control form-control-inline input-sm"
                    :disabled="allowedQualities.length === 0"
                >
                    <option
                        v-for="quality in validQualities"
                        :key="`quality-list-${quality.key}`"
                        :value="quality.value"
                    >
                        {{ quality.name }}
                    </option>
                </select>
            </div>
        </div>

        <div v-if="selectedQualityPreset !== 'keep'">
            <div v-if="(allowedQualities.length + preferredQualities.length) >= 1" id="qualityExplanation">
                <h5><b>Quality setting explanation:</b></h5>
                <h5 v-if="preferredQualities.length === 0">
                    This will download <b>any</b> of these qualities and then stops searching:
                    <label id="allowedExplanation">{{ explanation.allowed.join(', ') }}</label>
                </h5>
                <template v-else>
                    <h5>
                        Downloads <b>any</b> of these qualities:
                        <label id="allowedPreferredExplanation">{{ explanation.allowed.join(', ') }}</label>
                    </h5>
                    <h5>
                        But it will stop searching when one of these is downloaded:
                        <label id="preferredExplanation">{{ explanation.preferred.join(', ') }}</label>
                    </h5>
                </template>
            </div>
            <div v-else>Please select at least one allowed quality.</div>
        </div>

        <div v-if="backloggedEpisodes">
            <h5 class="{ 'red-text': !backloggedEpisodes.status }" v-html="backloggedEpisodes.html" />
        </div>

        <div v-if="archive" id="archive">
            <h5>
                <b>Archive downloaded episodes that are not currently in
                    <app-link href="manage/backlogOverview/" target="_blank" class="backlog-link">backlog</app-link>.</b>
                <br>Avoids unnecessarily increasing your backlog
                <br>
            </h5>
            <button
                @click.prevent="archiveEpisodes"
                :disabled="archiveButton.disabled"
                class="btn-medusa btn-inline"
            >
                {{ archiveButton.text }}
            </button>
            <h5>{{ archivedStatus }}</h5>
        </div>
    </div>
</template>
<script>
import { mapGetters, mapState } from 'vuex';

import { api } from '../../api';
import AppLink from './app-link';

export default {
    name: 'quality-chooser',
    components: {
        AppLink
    },
    props: {
        overallQuality: {
            type: Number,
            default: window.qualityChooserInitialQuality
        },
        keep: {
            type: String,
            default: null,
            validator: value => ['keep', 'show'].includes(value)
        },
        showSlug: {
            type: String
        }
    },
    data() {
        return {
            // eslint-disable-next-line no-warning-comments
            lock: false, // FIXME: Remove this hack, see `watch.overallQuality` below
            allowedQualities: [],
            preferredQualities: [],
            curQualityPreset: null,
            archive: false,
            archivedStatus: '',
            archiveButton: {
                text: 'Archive episodes',
                disabled: false
            }
        };
    },
    computed: {
        ...mapState({
            qualityValues: state => state.config.consts.qualities.values,
            qualityPresets: state => state.config.consts.qualities.presets,
            defaultQuality: state => state.config.general.showDefaults.quality
        }),
        ...mapGetters([
            'getQualityPreset',
            'splitQuality'
        ]),
        initialQuality() {
            return this.overallQuality === undefined ? this.defaultQuality : this.overallQuality;
        },
        selectedQualityPreset: {
            get() {
                return this.curQualityPreset;
            },
            set(newValue) {
                const { curQualityPreset, setQualityFromPreset } = this;
                // If an array was provided - initial or update from parent: [newPreset, oldPreset]
                // If a single value was provided - updated using select box: [newPreset, currentPreset]
                const [newPreset, currentPreset] = Array.isArray(newValue) ? newValue : [newValue, curQualityPreset];
                setQualityFromPreset(newPreset, currentPreset);
                this.curQualityPreset = newPreset;
            }
        },
        explanation() {
            const { allowedQualities, preferredQualities, qualityValues } = this;
            return qualityValues
                .reduce((result, { value, name }) => {
                    const isPreferred = preferredQualities.includes(value);
                    // If this quality is preferred but not allowed, add it to allowed
                    if (allowedQualities.includes(value) || isPreferred) {
                        result.allowed.push(name);
                    }
                    if (isPreferred) {
                        result.preferred.push(name);
                    }
                    return result;
                }, { allowed: [], preferred: [] });
        },
        validQualities() {
            return this.qualityValues.filter(({ key }) => key !== 'na');
        }
    },
    asyncComputed: {
        async backloggedEpisodes() {
            const { showSlug, allowedQualities, preferredQualities } = this;

            // Skip if no showSlug, as that means we're on a addShow page
            if (!showSlug) {
                return null;
            }

            // Skip if no qualities are selected
            if ((allowedQualities.length + preferredQualities.length) === 0) {
                return null;
            }

            const url = `series/${showSlug}/legacy/backlogged`;
            const params = {
                allowed: allowedQualities.join(','),
                preferred: preferredQualities.join(',')
            };
            let status = false; // Set to `false` for red text, `true` for normal color
            let response;
            try {
                response = await api.get(url, { params });
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
                html += "This change won't affect your backlogged episodes";
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
        this.setInitialPreset(this.initialQuality);
    },
    methods: {
        isQualityPreset(quality) {
            return this.getQualityPreset({ value: quality }) !== undefined;
        },
        setInitialPreset(preset) {
            const { isQualityPreset, keep } = this;
            const newPreset = keep === 'keep' ? 'keep' : (isQualityPreset(preset) ? preset : 0);
            this.selectedQualityPreset = [newPreset, preset];
        },
        async archiveEpisodes() {
            this.archivedStatus = 'Archiving...';

            const url = `series/${this.showSlug}/operation`;
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
            if (preset === undefined || preset === null) {
                return;
            }

            // [Mass Edit] If changing to/from `keep`, restore the original value
            if ([preset, oldPreset].some(val => val === 'keep')) {
                preset = this.initialQuality;
            // If preset is custom, set to last preset (provided it's not null)
            } else if ((preset === 0 || !this.isQualityPreset(preset)) && oldPreset !== null) {
                preset = oldPreset;
            }

            const { allowed, preferred } = this.splitQuality(preset);
            this.allowedQualities = allowed;
            this.preferredQualities = preferred;
        }
    },
    watch: {
        // eslint-disable-next-line no-warning-comments
        /*
        FIXME: Remove this watch and the `this.lock` hack.
        This is causing the preset selector to change from `Custom` to a preset,
        when the correct qualities for that preset are selected.
        */
        overallQuality(newValue) {
            if (!this.lock) {
                this.setInitialPreset(newValue);
            }
        },
        /* eslint-disable no-warning-comments */
        allowedQualities(newQuality) {
            // Deselecting all allowed qualities clears the preferred selection
            if (newQuality.length === 0 && this.preferredQualities.length > 0) {
                this.preferredQualities = [];
            }

            this.lock = true; // FIXME: Remove this hack, see above
            this.$emit('update:quality:allowed', newQuality);
            // FIXME: Remove this hack, see above
            this.$nextTick(() => {
                this.lock = false;
            });
        },
        preferredQualities(newQuality) {
            this.lock = true; // FIXME: Remove this hack, see above
            this.$emit('update:quality:preferred', newQuality);
            // FIXME: Remove this hack, see above
            this.$nextTick(() => {
                this.lock = false;
            });
        }
        /* eslint-enable no-warning-comments */
    }
};
</script>

<style scoped>
/* Put both custom quality selectors in the same row */
#customQualityWrapper > div {
    display: inline-block;
    text-align: left;
}

/* Put some distance between the two selectors */
#customQualityWrapper > div:first-of-type {
    padding-right: 30px;
}

.backlog-link {
    color: blue;
    text-decoration: underline;
}
</style>
