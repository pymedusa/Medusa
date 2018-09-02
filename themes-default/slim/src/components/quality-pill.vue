<template>
    <span :title="title" :class="pill.class">{{ pill.text }}</span>
</template>

<script>
import { mapState } from 'vuex';

/**
 * @typedef {Object} Quality
 * @property {number[]} allowed - Allowed qualities
 * @property {number[]} preferred - Preferred qualities
 */

export default {
    name: 'quality-pill',
    props: {
        quality: {
            type: Number,
            required: true,
            validator: value => value >= 0
        },
        showTitle: {
            type: Boolean,
            default: false
        },
        override: {
            type: Object,
            default: () => ({}),
            validator: value => {
                return Object.keys(value).every(key => ['class', 'title', 'text'].includes(key));
            }
        }
    },
    computed: {
        ...mapState({
            qualityValues: state => state.qualities.values,
            qualityValueStrings: state => state.qualities.strings.values,
            qualityAnySets: state => state.qualities.anySets,
            qualityAnySetStrings: state => state.qualities.strings.anySets,
            qualityPresets: state => state.qualities.presets,
            qualityPresetStrings: state => state.qualities.strings.presets,
            qualityCssClassStrings: state => state.qualities.strings.cssClass
        }),
        qualities() {
            const { quality, splitQuality } = this;
            return splitQuality(quality);
        },
        title() {
            const { override, qualities, qualityValueStrings, showTitle } = this;

            if (override.title) {
                return override.title;
            }

            if (!showTitle) {
                return undefined;
            }

            let title = '';
            title += 'Allowed Quality:\n';
            if (qualities.allowed.length === 0) {
                title += '  None';
            } else {
                title += qualities.allowed.map(curQual => `  ${qualityValueStrings[curQual]}`).join('\n');
            }

            title += '\n\nPreferred Quality:\n';
            if (qualities.preferred.length === 0) {
                title += '  None';
            } else {
                title += qualities.preferred.map(curQual => `  ${qualityValueStrings[curQual]}`).join('\n');
            }

            return title;
        },
        pill() { // eslint-disable-line complexity
            let { quality } = this;

            // If allowed and preferred qualities are the same, show pill as allowed quality
            const sumAllowed = (quality & 0xFFFF) >>> 0; // Unsigned int
            const sumPreferred = (quality >> 16) >>> 0; // Unsigned int
            if (sumAllowed === sumPreferred) {
                quality = sumAllowed;
            }

            const {
                isSubsetOf,
                qualities,
                qualityAnySets,
                qualityAnySetStrings,
                qualityCssClassStrings,
                qualityPresets,
                qualityPresetStrings,
                qualityValues,
                qualityValueStrings
            } = this;
            let cssClass;
            let text;

            const setHDTV = [qualityValues.hdtv, qualityValues.rawhdtv, qualityValues.fullhdtv, qualityValues.uhd4ktv, qualityValues.uhd8ktv];
            const setWEBDL = [qualityValues.hdwebdl, qualityValues.fullhdwebdl, qualityValues.uhd4kwebdl, qualityValues.uhd8kwebdl];
            const setBluRay = [qualityValues.hdbluray, qualityValues.fullhdbluray, qualityValues.uhd4kbluray, qualityValues.uhd8kbluray];
            const set720p = [qualityValues.hdtv, qualityValues.rawhdtv, qualityValues.hdwebdl, qualityValues.hdbluray];
            const set1080p = [qualityValues.fullhdtv, qualityValues.fullhdwebdl, qualityValues.fullhdbluray];
            const setUHD4K = [qualityValues.uhd4ktv, qualityValues.uhd4kwebdl, qualityValues.uhd4kbluray];
            const setUHD8K = [qualityValues.uhd8ktv, qualityValues.uhd8kwebdl, qualityValues.uhd8kbluray];

            // Is quality a preset?
            if (Object.values(qualityPresets).includes(quality)) {
                cssClass = qualityPresetStrings[quality];
                text = qualityPresetStrings[quality];
            // Is quality an 'anySet'? (any HDTV, any WEB-DL, any BluRay)
            } else if (Object.values(qualityAnySets).includes(quality)) {
                cssClass = qualityCssClassStrings[quality];
                text = qualityAnySetStrings[quality];
            // Is quality a specific quality? (720p HDTV, 1080p WEB-DL, etc.)
            } else if (Object.values(qualityValues).includes(quality)) {
                cssClass = qualityCssClassStrings[quality];
                text = qualityValueStrings[quality];
            // Check if all sources are HDTV
            } else if (isSubsetOf(qualities.allowed, setHDTV) && isSubsetOf(qualities.preferred, setHDTV)) {
                cssClass = qualityCssClassStrings[qualityAnySets.anyhdtv];
                text = 'HDTV';
            // Check if all sources are WEB-DL
            } else if (isSubsetOf(qualities.allowed, setWEBDL) && isSubsetOf(qualities.preferred, setWEBDL)) {
                cssClass = qualityCssClassStrings[qualityAnySets.anywebdl];
                text = 'WEB-DL';
            // Check if all sources are BluRay
            } else if (isSubsetOf(qualities.allowed, setBluRay) && isSubsetOf(qualities.preferred, setBluRay)) {
                cssClass = qualityCssClassStrings[qualityAnySets.anybluray];
                text = 'BluRay';
            // Check if all resolutions are 720p
            } else if (isSubsetOf(qualities.allowed, set720p) && isSubsetOf(qualities.preferred, set720p)) {
                cssClass = qualityCssClassStrings[qualityValues.hdbluray];
                text = '720p';
            // Check if all resolutions are 1080p
            } else if (isSubsetOf(qualities.allowed, set1080p) && isSubsetOf(qualities.preferred, set1080p)) {
                cssClass = qualityCssClassStrings[qualityValues.fullhdbluray];
                text = '1080p';
            // Check if all resolutions are 4K UHD
            } else if (isSubsetOf(qualities.allowed, setUHD4K) && isSubsetOf(qualities.preferred, setUHD4K)) {
                cssClass = qualityCssClassStrings[qualityValues.hdbluray];
                text = '4K-UHD';
            // Check if all resolutions are 8K UHD
            } else if (isSubsetOf(qualities.allowed, setUHD8K) && isSubsetOf(qualities.preferred, setUHD8K)) {
                cssClass = qualityCssClassStrings[qualityValues.hdbluray];
                text = '8K-UHD';
            } else {
                cssClass = 'Custom';
                text = 'Custom';
            }

            const { override } = this;
            return {
                class: override.class || ['quality', cssClass],
                text: override.text || text
            };
        }
    },
    methods: {
        /**
         * Split a combined quality to allowed and preferred qualities.
         * Converted Python method from `medusa.common.Quality.split_quality`.
         * @param {number} quality - The combined quality to split
         * @returns {Quality} - The split quality
         */
        splitQuality(quality) {
            const { qualityValues } = this;
            // Sort the quality list first
            const qualities = [...Object.values(qualityValues)].sort((a, b) => a - b);
            return qualities.reduce((result, curQuality) => {
                quality >>>= 0; // Unsigned int
                if (curQuality & quality) {
                    result.allowed.push(curQuality);
                }
                if ((curQuality << 16) & quality) {
                    result.preferred.push(curQuality);
                }
                return result;
            }, { allowed: [], preferred: [] });
        },
        /**
         * Check if all the items of `set1` are items of `set2`.
         * Assumption: Each array contains unique items only.
         * Source: https://stackoverflow.com/a/48211214/7597273
         * @param {(number[]|string[])} set1 - Array to be compared against `set2`.
         * @param {(number[]|string[])} set2 - Array to compare `set1` against.
         * @returns {boolean} - Whether or not `set1` is a subset of `set2`
         */
        isSubsetOf(set1, set2) {
            return set1.every(value => set2.includes(value));
        }
    }
};
</script>

<style scoped>
.quality {
    font: 12px/13px "Open Sans", verdana, sans-serif;
    background-image: -webkit-linear-gradient(top, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0) 50%, rgba(0, 0, 0, 0) 50%, rgba(0, 0, 0, 0.25));
    background-image: -moz-linear-gradient(top, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0) 50%, rgba(0, 0, 0, 0) 50%, rgba(0, 0, 0, 0.25));
    background-image: -o-linear-gradient(top, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0) 50%, rgba(0, 0, 0, 0) 50%, rgba(0, 0, 0, 0.25));
    background-image: linear-gradient(to bottom, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0) 50%, rgba(0, 0, 0, 0) 50%, rgba(0, 0, 0, 0.25));
    box-shadow: inset 0 1px rgba(255, 255, 255, 0.1), inset 0 -1px 3px rgba(0, 0, 0, 0.3), inset 0 0 0 1px rgba(255, 255, 255, 0.08), 0 1px 2px rgba(0, 0, 0, 0.15);
    text-shadow: 0 1px rgba(0, 0, 0, 0.8);
    color: rgb(255, 255, 255);
    display: inline-block;
    padding: 2px 4px;
    text-align: center;
    vertical-align: baseline;
    border-radius: 4px;
    white-space: nowrap;
}

.any-hd {
    background-color: rgb(38, 114, 182);
    /* stylelint-disable declaration-block-no-shorthand-property-overrides */
    background:
        repeating-linear-gradient(
        -45deg,
        rgb(38, 114, 182),
        rgb(38, 114, 182) 10px,
        rgb(91, 153, 13) 10px,
        rgb(91, 153, 13) 20px
    );
    /* stylelint-enable */
}

.Custom {
    background-color: rgb(98, 25, 147);
}

.HD {
    background-color: rgb(38, 114, 182);
}

.HDTV {
    background-color: rgb(38, 114, 182);
}

.HD720p {
    background-color: rgb(91, 153, 13);
}

.HD1080p {
    background-color: rgb(38, 114, 182);
}

.UHD-4K {
    background-color: rgb(117, 0, 255);
}

.UHD-8K {
    background-color: rgb(65, 0, 119);
}

.RawHD {
    background-color: rgb(205, 115, 0);
}

.RawHDTV {
    background-color: rgb(205, 115, 0);
}

.SD {
    background-color: rgb(190, 38, 37);
}

.SDTV {
    background-color: rgb(190, 38, 37);
}

.SDDVD {
    background-color: rgb(190, 38, 37);
}

.Any {
    background-color: rgb(102, 102, 102);
}

.Unknown {
    background-color: rgb(153, 153, 153);
}

.Proper {
    background-color: rgb(63, 127, 0);
}
</style>
