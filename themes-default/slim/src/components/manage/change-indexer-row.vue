<template>
    <tr ref="changeIndexerRow">
        <td><input type="checkbox" v-model="show.checked" :data-slug="show.id.slug"></td>
        <td>{{show.name}}</td>
        <td>{{show.indexer}}</td>
        <td><select-indexer v-bind="{show, searchedShow}" @change="selectIndexerChange" /></td>
    </tr>
</template>
<script>
import { mapGetters } from 'vuex';
import SelectIndexer from './select-indexer.vue';
import NewShowSearch from '../new-show-search.vue';

export default {
    name: 'change-indexer-row',
    components: {
        SelectIndexer
    },
    props: {
        show: Object
    },
    data() {
        return {
            // Keep track of the manual searched/selected show.
            searchedShow: {
                searched: false,
                indexer: null,
                id: null
            },
            displaySearch: false,
            searchComponent: null
        }
    },
    computed: {
        ...mapGetters(['indexerIdToName'])
    },
    methods: {
        selectIndexerChange({text, value}) {
            const { show } = this;

            this.displaySearch = text === '--search--';
            if (text === '--search--') {
                this.displaySearchComponent();
            } else {
                this.$emit('selected', { show, indexer: text, showId: value });
            }
        },
        displaySearchComponent() {
            const NewShowSearchClass = Vue.extend(NewShowSearch);
            const { indexerIdToName, show } = this;
            this.searchComponent = new NewShowSearchClass({
                propsData: {
                    providedInfo: {
                        showName: show.name
                    },
                    fromChangeIndexer: true
                },
                parent: this
            });

            // Bind the 'added' event to the newShow vm.
            this.searchComponent.$on('selected', ({ result }) => {
                this.searchedShow.searched = true;
                this.searchedShow.indexer = indexerIdToName(result.indexerId);
                this.searchedShow.id = result.showId;
            });

            // Bind the 'added' event to the newShow vm.
            this.searchComponent.$on('close', () => {
                this.searchComponent.$destroy();
                // Remove the element from the DOM
                this.searchComponent.$el.closest('tr').remove();
            });

            // Need these, because we want it to span the width of the parent table row.
            const row = document.createElement('tr');
            row.style.columnSpan = 'all';
            const cell = document.createElement('td');
            cell.setAttribute('colspan', '9999');

            const wrapper = document.createElement('div'); // Just used to mount on.
            row.append(cell);
            cell.append(wrapper);
            this.$refs.changeIndexerRow.after(row);

            this.searchComponent.$mount(wrapper);
            // Vue.set(addShowComponents, `curdirindex-${curDirIndex}`, instance);
        }
    },
}
</script>