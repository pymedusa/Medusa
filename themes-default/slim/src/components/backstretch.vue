<template>
    <div></div>
</template>
<script>
import { webRoot, apiKey } from '../api';

export default {
    name: 'backstretch',
    props: {
        opacity: {
            type: Number
        },
        indexer: {
            type: String
        },
        id: {
            type: [String, Number]
        }
    },
    computed: {
        offset() {
            let offset = '90px';
            if ($('#sub-menu-container').length === 0) {
                offset = '50px';
            }
            if ($(window).width() < 1280) {
                offset = '50px';
            }
            return offset;
        }
    },
    mounted() {
        const { $el, opacity, indexer, id, offset } = this;
        const el = $($el);

        const showSlug = indexer + String(id);

        if (indexer && id) {
            $.backstretch(webRoot + '/api/v2/series/' + showSlug + '/asset/fanart?api_key=' + apiKey);
            el.css('top', offset);
            el.css('opacity', opacity).fadeIn(500);
        }
    }
};
</script>
<style>

</style>
