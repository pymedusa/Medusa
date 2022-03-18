<template>
    <input
        type="text" :placeholder="sceneAbsolute" size="6" maxlength="8"
        class="sceneAbsolute form-control input-scene addQTip"
        title="Change this value if scene absolute numbering differs from the indexer absolute numbering. Generally used for anime shows."
        :value="sceneAbsolute"
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
    name: 'scene-number-anime-input',
    props: {
        show: Object,
        initialEpisode: Object
    },
    data() {
        return {
            sceneAbsolute: this.initialEpisode.scene.absoluteNumber,
            isValid: null,
            numberingFrom: 'indexer'
        };
    },
    mounted() {
        this.getSceneAbsoluteNumbering();
    },
    computed: {
        ...mapState({
            client: state => state.auth.client
        })
    },
    methods: {
        changeSceneNumbering(event) {
            let { value } = event.currentTarget;
            // Strip non-numeric characters
            value = value.replace(/[^\dXx]*/g, '');
            const forAbsolute = this.initialEpisode.absoluteNumber;

            const m = value.match(/^(\d{1,3})$/i);
            let sceneAbsolute = null;
            if (m) {
                sceneAbsolute = m[1];
                this.isValid = true;
                this.sceneAbsolute = sceneAbsolute;
                this.setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute);
            }
        },
        async setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute) {
            const { $snotify, show } = this;

            if (!show.config.scene) {
                $snotify.warning(
                    'To change an anime episode scene numbering you need to enable the show option `scene` first',
                    'Warning',
                    { timeout: 0 }
                );
            }

            if (sceneAbsolute === '') {
                sceneAbsolute = null;
            }

            try {
                const { data } = await this.client.apiRoute.get('home/setSceneNumbering', { params: {
                    showslug: show.id.slug,
                    // eslint-disable-next-line camelcase
                    for_absolute: forAbsolute,
                    // eslint-disable-next-line camelcase
                    scene_absolute: sceneAbsolute
                } });
                if (data.success) {
                    if (data.sceneAbsolute === null) {
                        this.sceneAbsolute = '';
                    } else {
                        this.sceneAbsolute = data.sceneAbsolute;
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
                    `Could not set absolute scene numbering for show ${show.id.slug} to ${sceneAbsolute}`,
                    'Error'
                );
            }
        },
        getSceneAbsoluteNumbering() {
            const { initialEpisode, show } = this;
            const { sceneAbsoluteNumbering, xemAbsoluteNumbering } = show;

            if (!show.config.anime || !show.config.scene) {
                return;
            }

            if (Object.keys(sceneAbsoluteNumbering).length > 0) {
                const mapped = sceneAbsoluteNumbering.filter(x => {
                    return x.absolute === initialEpisode.absoluteNumber;
                });
                if (mapped.length !== 0) {
                    this.sceneAbsolute = mapped[0].sceneAbsolute;
                    this.numberingFrom = 'custom';
                }
            } else if (Object.keys(xemAbsoluteNumbering).length > 0) {
                const mapped = xemAbsoluteNumbering.filter(x => {
                    return x.absolute === initialEpisode.absoluteNumber;
                });
                if (mapped.length !== 0) {
                    this.sceneAbsolute = mapped[0].sceneAbsolute;
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
