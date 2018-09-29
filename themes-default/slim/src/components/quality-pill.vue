<template>
    <span :class="override.class || ['quality', pill.class]" :title="title">{{ override.text || pill.text }}</span>
</template>

<script>
import { mapState } from 'vuex';

/**
 * An object representing a split quality.
 *
 * @typedef {Object} Quality
 * @property {number[]} allowed - Allowed qualities
 * @property {number[]} preferred - Preferred qualities
 */
export default {
    name: 'quality-pill',
    props: {
        allowed: {
            type: Array
        },
        preferred: {
            type: Array
        },
        quality: {
            type: Number,
            validator: value => (value >>> 0) >= 0 // Unsigned int
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
            const { allowed, preferred, quality, splitQuality } = this;

            // Used for Vueified pages as they have the arrays already split
            if (allowed && preferred) {
                return {
                    allowed,
                    preferred
                };
            }
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
        setHDTV() {
            return this.makeQualitySet('hdtv', 'rawhdtv', 'fullhdtv', 'uhd4ktv', 'uhd8ktv');
        },
        setWEBDL() {
            return this.makeQualitySet('hdwebdl', 'fullhdwebdl', 'uhd4kwebdl', 'uhd8kwebdl');
        },
        setBluRay() {
            return this.makeQualitySet('hdbluray', 'fullhdbluray', 'uhd4kbluray', 'uhd8kbluray');
        },
        set720p() {
            return this.makeQualitySet('hdtv', 'rawhdtv', 'hdwebdl', 'hdbluray');
        },
        set1080p() {
            return this.makeQualitySet('fullhdtv', 'fullhdwebdl', 'fullhdbluray');
        },
        setUHD4K() {
            return this.makeQualitySet('uhd4ktv', 'uhd4kwebdl', 'uhd4kbluray');
        },
        setUHD8K() {
            return this.makeQualitySet('uhd8ktv', 'uhd8kwebdl', 'uhd8kbluray');
        },
        pill() {
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
                qualityValueStrings,
                setHDTV,
                setWEBDL,
                setBluRay,
                set720p,
                set1080p,
                setUHD4K,
                setUHD8K
            } = this;

            // This are the fallback values, if none of the checks below match
            const result = {
                class: 'Custom',
                text: 'Custom'
            };

            // Is quality a preset?
            if (Object.values(qualityPresets).includes(quality)) {
                result.class = qualityPresetStrings[quality];
                result.text = qualityPresetStrings[quality];
            // Is quality an 'anySet'? (any HDTV, any WEB-DL, any BluRay)
            } else if (Object.values(qualityAnySets).includes(quality)) {
                result.class = qualityCssClassStrings[quality];
                result.text = qualityAnySetStrings[quality];
            // Is quality a specific quality? (720p HDTV, 1080p WEB-DL, etc.)
            } else if (Object.values(qualityValues).includes(quality)) {
                result.class = qualityCssClassStrings[quality];
                result.text = qualityValueStrings[quality];
            // Check if all sources are HDTV
            } else if (isSubsetOf(qualities.allowed, setHDTV) && isSubsetOf(qualities.preferred, setHDTV)) {
                result.class = qualityCssClassStrings[qualityAnySets.anyhdtv];
                result.text = 'HDTV';
            // Check if all sources are WEB-DL
            } else if (isSubsetOf(qualities.allowed, setWEBDL) && isSubsetOf(qualities.preferred, setWEBDL)) {
                result.class = qualityCssClassStrings[qualityAnySets.anywebdl];
                result.text = 'WEB-DL';
            // Check if all sources are BluRay
            } else if (isSubsetOf(qualities.allowed, setBluRay) && isSubsetOf(qualities.preferred, setBluRay)) {
                result.class = qualityCssClassStrings[qualityAnySets.anybluray];
                result.text = 'BluRay';
            // Check if all resolutions are 720p
            } else if (isSubsetOf(qualities.allowed, set720p) && isSubsetOf(qualities.preferred, set720p)) {
                result.class = qualityCssClassStrings[qualityValues.hdbluray];
                result.text = '720p';
            // Check if all resolutions are 1080p
            } else if (isSubsetOf(qualities.allowed, set1080p) && isSubsetOf(qualities.preferred, set1080p)) {
                result.class = qualityCssClassStrings[qualityValues.fullhdbluray];
                result.text = '1080p';
            // Check if all resolutions are 4K UHD
            } else if (isSubsetOf(qualities.allowed, setUHD4K) && isSubsetOf(qualities.preferred, setUHD4K)) {
                result.class = qualityCssClassStrings[qualityValues.uhd4kbluray];
                result.text = 'UHD-4K';
            // Check if all resolutions are 8K UHD
            } else if (isSubsetOf(qualities.allowed, setUHD8K) && isSubsetOf(qualities.preferred, setUHD8K)) {
                result.class = qualityCssClassStrings[qualityValues.uhd8kbluray];
                result.text = 'UHD-8K';
            }

            return result;
        }
    },
    methods: {
        /**
         * Split a combined quality to allowed and preferred qualities.
         * Converted Python method from `medusa.common.Quality.split_quality`.
         *
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
        makeQualitySet(...keys) {
            return keys.map(key => this.qualityValues[key]);
        },
        /**
         * Check if all the items of `set1` are items of `set2`.
         * Assumption: Each array contains unique items only.
         * Source: https://stackoverflow.com/a/48211214/7597273
         *
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
