<template>
    <div class="select-trakt-list max-width">
        <ul>
            <li v-for="availableList of availableLists" :key="availableList">
                <div class="trakt-list-group">
                    <input disabled class="form-control input-sm available-list" type="text" :value="availableList">
                    <input type="checkbox" :checked="selectedLists.find(list => list === availableList)" @input="saveLists($event, availableList)">
                </div>
            </li>
        </ul>
    </div>
</template>
<script>

import { mapActions, mapState } from 'vuex';

export default {
    name: 'select-trakt-list',
    computed: {
        ...mapState({
            availableLists: state => state.config.general.recommended.trakt.availableLists,
            selectedLists: state => state.config.general.recommended.trakt.selectedLists,
            general: state => state.config.general
        })
    },
    methods: {
        ...mapActions(['setTraktSelectedLists']),
        saveLists(event, currentList) {
            const { selectedLists, setTraktSelectedLists } = this;
            const isChecked = event.currentTarget.checked;
            // Add to list
            if (isChecked && !selectedLists.includes(currentList)) {
                selectedLists.push(currentList);
            }

            // Remove from list
            const newList = selectedLists.filter(list => list !== currentList || (currentList && isChecked));
            setTraktSelectedLists(newList);
        }
    }
};
</script>
<style scoped>
ul {
    padding-left: 0;
}

li {
    list-style-type: none;
}

.trakt-list-group {
    display: inline-flex;
    height: 25px;
}

input {
    display: inline-block;
    box-sizing: border-box;
}

input.available-list {
    height: 22px;
}

input[type=checkbox] {
    width: 20px;
    height: 20px;
}

.max-width {
    max-width: 450px;
}
</style>
