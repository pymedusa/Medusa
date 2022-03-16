<template>
    <div class="align-center">
        <select name="indexer" v-model="selectedIndexer" @change="$emit('change', selectedIndexer)">
            <option disabled value="--select--">--select--</option>
            <option
                v-for="option in externalsOptions"
                :key="option.value"
                :value="{value: option.value, text: option.text}"
            >
                {{option.text}}
            </option>
        </select>
        <div v-if="searchedShow && searchedShow.searched" class="star" title="This indexer was manually selected">*</div>
    </div>
</template>
<script>

export default {
    name: 'select-indexer',
    props: {
        show: Object,
        searchedShow: Object
    },
    data() {
        return {
            selectedIndexer: '--select--',
            searchedIndexer: null,
            searchedIndexerId: null,
            allowedIndexers: ['tvdb', 'tmdb', 'tvmaze', 'imdb']
        };
    },
    computed: {
        externalsOptions() {
            const { allowedIndexers, searchedShow, show } = this;
            const { externals } = show;
            let options = [];
            options = Object.keys(externals)
                .filter(key => allowedIndexers.includes(key))
                .filter(key => key !== show.indexer)
                .map(key => ({ text: key, value: externals[key] }));
            options.push({ text: '--search--', value: '--search--' });

            if (searchedShow && searchedShow.searched) {
                const newOption = options.find(option => option.text === searchedShow.indexer);
                if (newOption) {
                    newOption.value = searchedShow.id;
                    newOption.searched = true;
                } else {
                    options.push({ text: searchedShow.indexer, value: searchedShow.id, searched: true });
                }
            }
            return options;
        }
    },
    watch: {
        searchedShow: {
            handler(searchedShow) {
                if (searchedShow && searchedShow.searched) {
                    this.selectedIndexer = { value: searchedShow.id, text: searchedShow.indexer };
                }
            },
            deep: true
        }
    }
};
</script>
<style scoped>
.star {
    position: absolute;
    top: 0;
    right: 0;
}
</style>
