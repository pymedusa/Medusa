<template>
    <div class="show-option pull-right">
        Poster Size:
        <div style="width: 100px; display: inline-block; margin-left: 7px;" id="posterSizeSlider" />
    </div>
</template>
<script>
import { mapActions } from 'vuex';

export default {
    name: 'poster-size-slider',
    props: {
        min: {
            type: Number,
            default: 75
        },
        max: {
            type: Number,
            default: 250
        }
    },
    mounted() {
        const { setLayoutLocal, min, max } = this;

        // Get poster size from localStorage
        let slidePosterSize;
        if (typeof (Storage) !== 'undefined') {
            slidePosterSize = Number.parseInt(localStorage.getItem('posterSize'), 10);
        }
        if (typeof (slidePosterSize) !== 'number' || Number.isNaN(slidePosterSize)) {
            slidePosterSize = 188;
        }

        // Update poster size to store
        setLayoutLocal({ key: 'posterSize', value: slidePosterSize });

        $(this.$el).find('#posterSizeSlider').slider({
            min,
            max,
            value: slidePosterSize,
            change(e, ui) {
                // Save to localStorage
                if (typeof (Storage) !== 'undefined') {
                    localStorage.setItem('posterSize', ui.value);
                }
                // Save to store
                setLayoutLocal({ key: 'posterSize', value: ui.value });
            }
        });
    },
    methods: {
        ...mapActions({
            setLayoutLocal: 'setLayoutLocal'
        })
    }
};
</script>
<style>

</style>
