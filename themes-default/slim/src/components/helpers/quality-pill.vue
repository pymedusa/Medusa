<template>
    <span :class="override.class || ['quality', pill.key]" :title="title">{{ override.text || pill.name }}</span>
</template>

<script>
import { mapGetters, mapState } from 'vuex';
import { combineQualities } from '../../utils/core';

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
                return Object.keys(value).every(key => ['class', 'title', 'text', 'style'].includes(key));
            }
        }
    },
    computed: {
        ...mapState({
            qualityValues: state => state.config.consts.qualities.values
        }),
        ...mapGetters([
            'getQuality',
            'getQualityAnySet',
            'getQualityPreset',
            'splitQuality'
        ]),
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
            const { override, qualities, getQuality, showTitle } = this;

            if (override.title) {
                return override.title;
            }

            if (!showTitle) {
                return undefined;
            }

            const getQualityName = value => getQuality({ value }).name;

            let title = '';
            title += 'Allowed Qualities:\n';
            if (qualities.allowed.length === 0) {
                title += '  None';
            } else {
                title += qualities.allowed.map(curQual => `  ${getQualityName(curQual)}`).join('\n');
            }

            title += '\n\nPreferred Qualities:\n';
            if (qualities.preferred.length === 0) {
                title += '  None';
            } else {
                title += qualities.preferred.map(curQual => `  ${getQualityName(curQual)}`).join('\n');
            }

            return title;
        },
        pill() {
            let { quality, allowed, preferred } = this;

            // Combine allowed & preferred qualities
            if (allowed && preferred) {
                quality = combineQualities(allowed, preferred);
            }

            // If allowed and preferred qualities are the same, show pill as allowed quality
            const sumAllowed = (quality & 0xFFFF) >>> 0; // Unsigned int
            const sumPreferred = (quality >> 16) >>> 0; // Unsigned int
            if (sumAllowed === sumPreferred) {
                quality = sumAllowed;
            }

            const matched =
                // Is quality a preset?
                this.getQualityPreset({ value: quality }) ||
                // Is quality an 'anySet'? (any HDTV, any WEB-DL, any BluRay)
                this.getQualityAnySet({ value: quality }) ||
                // Is quality a specific quality? (720p HDTV, 1080p WEB-DL, etc.)
                this.getQuality({ value: quality });

            if (matched !== undefined) {
                return matched;
            }

            const customQualitySets = [
                // All sources are HDTV
                {
                    name: 'HDTV',
                    key: 'anyhdtv',
                    elements: ['hdtv', 'rawhdtv', 'fullhdtv', 'uhd4ktv', 'uhd8ktv']
                },
                // All sources are WEB-DL
                {
                    name: 'WEB-DL',
                    key: 'anywebdl',
                    elements: ['hdwebdl', 'fullhdwebdl', 'uhd4kwebdl', 'uhd8kwebdl']
                },
                // All sources are BluRay
                {
                    name: 'BluRay',
                    key: 'anybluray',
                    elements: ['hdbluray', 'fullhdbluray', 'uhd4kbluray', 'uhd8kbluray']
                },
                // All resolutions are 720p
                {
                    name: '720p',
                    key: 'hd720p',
                    elements: ['hdtv', 'rawhdtv', 'hdwebdl', 'hdbluray']
                },
                // All resolutions are 1080p
                {
                    name: '1080p',
                    key: 'hd1080p',
                    elements: ['fullhdtv', 'fullhdwebdl', 'fullhdbluray']
                },
                // All resolutions are 4K UHD
                {
                    name: 'UHD-4K',
                    key: 'anyuhd4k',
                    elements: ['uhd4ktv', 'uhd4kwebdl', 'uhd4kbluray']
                },
                // All resolutions are 8K UHD
                {
                    name: 'UHD-8K',
                    key: 'anyuhd8k',
                    elements: ['uhd8ktv', 'uhd8kwebdl', 'uhd8kbluray']
                }
            ];

            const { isSubsetOf, qualities, makeQualitySet } = this;

            for (const { name, key, elements } of customQualitySets) {
                const qualitySet = makeQualitySet(elements);
                // Check if both quality lists match the set.
                if (isSubsetOf(qualities.allowed, qualitySet) && isSubsetOf(qualities.preferred, qualitySet)) {
                    return { name, key };
                }
            }

            // These are the fallback values, if none of the checks above matched
            return {
                key: 'custom',
                name: 'Custom'
            };
        }
    },
    methods: {
        /**
         * Make a quality set.
         * @param {string[]} keys - An array of quality keys to add their values to the set.
         * @returns {number[]} An array of the quality values.
         */
        makeQualitySet(keys) {
            return this.qualityValues.reduce((result, { key, value }) => {
                if (keys.includes(key)) {
                    return result.concat(value);
                }
                return result;
            }, []);
        },
        /**
         * Check if all the items of `set1` are items of `set2`.
         * Note that when `set1` is empty, it returns `true`.
         * Assumption: Each array contains unique items only.
         * Source: https://stackoverflow.com/a/48211214/7597273
         *
         * @param {(Number[]|String[])} set1 - Array to be compared against `set2`.
         * @param {(Number[]|String[])} set2 - Array to compare `set1` against.
         * @returns {Boolean} - Whether or not `set1` is a subset of `set2`
         */
        isSubsetOf(set1, set2) {
            return set1.every(value => set2.includes(value));
        }
    }
};
</script>

<style scoped>
/* Base class */
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

/* Custom */
.custom {
    background-color: rgb(98, 25, 147);
}

/* HD-720p + FHD-1080p */
.hd, /* Preset */
.anyhdtv, /* AnySet */
.anywebdl, /* AnySet */
.anybluray { /* AnySet */
    background-color: rgb(38, 114, 182);
    background-image:
        repeating-linear-gradient(
        -45deg,
        rgb(38, 114, 182),
        rgb(38, 114, 182) 10px,
        rgb(91, 153, 13) 10px,
        rgb(91, 153, 13) 20px
    );
}

/* HD-720p */
.hd720p, /* Preset */
.hdtv,
.hdwebdl,
.hdbluray {
    background-color: rgb(91, 153, 13);
}

/* FHD-1080p */
.hd1080p, /* Preset */
.fullhdtv,
.fullhdwebdl,
.fullhdbluray {
    background-color: rgb(38, 114, 182);
}

/* UHD-4K + UHD-8K */
.uhd { /* Preset */
    background-color: rgb(117, 0, 255);
    background-image:
        repeating-linear-gradient(
        -45deg,
        rgb(117, 0, 255),
        rgb(117, 0, 255) 10px,
        rgb(65, 0, 119) 10px,
        rgb(65, 0, 119) 20px
    );
}

/* UHD-4K */
.uhd4k, /* Preset */
.anyuhd4k, /* Custom Set */
.uhd4ktv,
.uhd4kwebdl,
.uhd4kbluray {
    background-color: rgb(117, 0, 255);
}

/* UHD-8K */
.uhd8k, /* Preset */
.anyuhd8k, /* Custom Set */
.uhd8ktv,
.uhd8kwebdl,
.uhd8kbluray {
    background-color: rgb(65, 0, 119);
}

/* RawHD/RawHDTV */
.rawhdtv {
    background-color: rgb(205, 115, 0);
}

/* SD */
.sd, /* Preset */
.sdtv,
.sddvd {
    background-color: rgb(190, 38, 37);
}

/* Any */
.any { /* Preset */
    background-color: rgb(102, 102, 102);
}

/* Unknown */
.unknown {
    background-color: rgb(153, 153, 153);
}

/* Proper (used on History page) */
.proper {
    background-color: rgb(63, 127, 0);
}
</style>
