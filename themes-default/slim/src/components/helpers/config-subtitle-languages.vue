<template>
    <div id="config-subtitle-languages">
        <vue-tags-input
            v-model="tag"
            :tags="wantedLanguages"
            :autocomplete-items="filteredItems"
            add-only-from-autocomplete
            placeholder="Write to search a language and select it"
            @tags-changed="tagsChanged"
        >
            <div slot="autocomplete-item" slot-scope="props" class="autocomplete-item"
                 @click="props.performAdd(props.item)"
            >
                <img :src="`images/subtitles/flags/${props.item.text}.png`" onError="this.onerror=null; this.src='images/flags/unknown.png';" style="vertical-align: middle !important;">
                {{props.item.name}}
            </div>

            <div slot="tag-left" slot-scope="props" class="country-left"
                 @click="props.performOpenEdit(props.index)"
            >
                <img :src="`images/subtitles/flags/${props.tag.text}.png`" onError="this.onerror=null; this.src='images/flags/unknown.png';" style="vertical-align: middle !important;">
            </div>
        </vue-tags-input>
    </div>
</template>

<script>
import { mapState } from 'vuex';
import VueTagsInput from '@johmun/vue-tags-input';

export default {
    name: 'config-subtitle-languages',
    components: {
        VueTagsInput
    },
    props: {
        languages: Array
    },
    data() {
        return {
            tag: '',
            wantedLanguages: []
        };
    },
    mounted() {
        const { languages } = this;
        this.wantedLanguages = languages.map(code => ({ text: code.id, name: code.name }));
    },
    computed: {
        ...mapState({
            subtitleCodeFilter: state => state.config.subtitles.codeFilter
        }),
        filteredItems() {
            return this.subtitleCodeFilter
                .map(code => ({ text: code.id, name: code.name }))
                .filter(i => {
                    return i.text.toLowerCase().includes(this.tag.toLowerCase());
                });
        }
    },
    methods: {
        updateValue() {
            const { wantedLanguages } = this;
            this.$emit('input', wantedLanguages);
        },
        tagsChanged(newTags) {
            this.wantedLanguages = newTags;
            this.$emit('change', newTags);
        }
    },
    watch: {
        languages(languages) {
            this.wantedLanguages = languages.map(code => ({ text: code.id, name: code.name }));
        }
    }
};
</script>

<style scoped>
.autocomplete-item {
    background: white;
    color: black;
}

</style>
