<template>
    <input
        type="text" :placeholder="`${sceneSeason || initialEpisode.season}x${sceneEpisode || initialEpisode.episode}`" size="6" maxlength="8"
        class="sceneSeasonXEpisode form-control input-scene addQTip"
        title="Change this value if scene numbering differs from the indexer episode numbering. Generally used for non-anime shows."
        :value="`${sceneSeason || initialEpisode.season}x${sceneEpisode || initialEpisode.episode}`"
        style="padding: 0; text-align: center; max-width: 60px;"
        :class="[
            isValid === true ? 'isValid' : '',
            isValid === false ? 'isInvalid' : '',
            numberingFrom === 'custom' ? 'isCustom' : ''
        ]"
        @change="changeSceneNumbering"
    >
</template>

<script>
import { mapState } from 'vuex';

export default {
    name: 'scene-number-input',
    props: {
        show: Object,
        initialEpisode: Object
    },
    data() {
        return {
            sceneSeason: this.initialEpisode.scene.season,
            sceneEpisode: this.initialEpisode.scene.episode,
            isValid: null,
            numberingFrom: 'indexer'
        };
    },
    mounted() {
        this.getSceneNumbering();
    },
    computed: {
        ...mapState({
            client: state => state.auth.client
        })
    },
    methods: {
        changeSceneNumbering(event) {
            let { value } = event.currentTarget;
            value = value.replace(/[^\dXx]*/g, '');
            const forSeason = this.initialEpisode.season;
            const forEpisode = this.initialEpisode.episode;

            // If empty reset the field
            if (value === '') {
                this.setEpisodeSceneNumbering(forSeason, forEpisode, null, null);
                return;
            }

            const m = value.match(/^(\d+)x(\d+)$/i);
            const onlyEpisode = value.match(/^(\d+)$/i);
            let sceneSeason = null;
            let sceneEpisode = null;
            if (m) {
                sceneSeason = m[1];
                sceneEpisode = m[2];
                this.isValid = true;
            } else if (onlyEpisode) {
                // For example when '5' is filled in instead of '1x5', asume it's the first season
                sceneSeason = forSeason;
                sceneEpisode = onlyEpisode[1];
                this.isValid = true;
            } else {
                this.isValid = false;
            }

            if (this.isValid) {
                this.sceneSeason = sceneSeason;
                this.sceneEpisode = sceneEpisode;
                this.setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode);
            }
        },
        async setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode) {
            const { $snotify, show } = this;

            if (!show.config.scene) {
                $snotify.warning(
                    'To change episode scene numbering you need to enable the show option `scene` first',
                    'Warning',
                    { timeout: 0 }
                );
            }

            if (sceneSeason === '') {
                sceneSeason = null;
            }

            if (sceneEpisode === '') {
                sceneEpisode = null;
            }

            try {
                const { data } = await this.client.apiRoute.get('home/setSceneNumbering', { params: {
                    showslug: show.id.slug,
                    // eslint-disable-next-line camelcase
                    for_season: forSeason,
                    // eslint-disable-next-line camelcase
                    for_episode: forEpisode,
                    // eslint-disable-next-line camelcase
                    scene_season: sceneSeason,
                    // eslint-disable-next-line camelcase
                    scene_episode: sceneEpisode
                } });
                if (data.success) {
                    if (data.sceneSeason === null || data.sceneEpisode === null) {
                        this.sceneSeason = '';
                        this.sceneEpisode = '';
                    } else {
                        this.sceneSeason = data.sceneSeason;
                        this.sceneEpisode = data.sceneEpisode;
                    }
                } else if (data.errorMessage) {
                    $snotify.error(
                        data.errorMessage,
                        'Error'
                    );
                } else {
                    $snotify.error(
                        'Update failed',
                        'Error'
                    );
                }
            } catch (error) {
                $snotify.error(
                    `Could not set scene numbering for show ${show.id.slug} to ${sceneSeason}x${sceneEpisode}`,
                    'Error'
                );
            }
        },
        /**
         * Check if the season/episode combination exists in the scene numbering.
         */
        getSceneNumbering() {
            const { show, initialEpisode } = this;
            const { sceneNumbering, xemNumbering } = show;

            const { season, episode } = initialEpisode;

            if (!show.config.scene) {
                this.sceneSeason = 0;
                this.sceneEpisode = 0;
            }

            // Manually configured scene numbering
            if (sceneNumbering.length > 0) {
                const mapped = sceneNumbering.filter(x => {
                    return x.source.season === season && x.source.episode === episode;
                });
                if (mapped.length > 0) {
                    this.sceneSeason = mapped[0].destination.season;
                    this.sceneEpisode = mapped[0].destination.episode;
                    this.numberingFrom = 'custom';
                }
            } else if (xemNumbering.length > 0) {
                // Scene numbering downloaded from thexem.de.
                const mapped = xemNumbering.filter(x => {
                    return x.source.season === season && x.source.episode === episode;
                });
                if (mapped.length > 0) {
                    this.sceneSeason = mapped[0].destination.season;
                    this.sceneEpisode = mapped[0].destination.episode;
                    this.numberingFrom = 'xem';
                }
            }
        }
    }
};
</script>

<style scoped>
.isValid {
    background-color: #90ee90;
    color: #fff;
    font-weight: bold;
}

.isInvalid {
    background-color: #f00;
    color: #fff !important;
    font-weight: bold;
}

.isCustom {
    background-color: #00ebaf;
    color: #fff !important;
    font-weight: bold;
}
</style>
