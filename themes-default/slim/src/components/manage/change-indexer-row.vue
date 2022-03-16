<template>
    <tr ref="changeIndexerRow">
        <td><input type="checkbox" v-model="currentShow.checked" :data-slug="show.id.slug"></td>
        <td><app-link :href="`home/displayShow?showslug=${show.id.slug}`">{{show.name}}</app-link></td>
        <td>{{show.indexer}}</td>
        <td><select-indexer v-bind="{show, searchedShow}" @change="selectIndexerChange" /></td>
        <td class="align-center">
            <div v-if="state" class="step-container">
                <div class="state">
                    <state-switch :state="state" />
                </div>
                <div class="stepdisplay">
                    <ul>
                        <li v-for="step of show.changeStatus.steps" :key="step">{{step}}</li>
                    </ul>
                </div>
            </div>
        </td>
    </tr>
</template>
<script>
import Vue from 'vue';
import { mapGetters, mapState } from 'vuex';
import SelectIndexer from './select-indexer.vue';
import NewShowSearch from '../new-show-search.vue';
import { AppLink, StateSwitch } from '../helpers';

export default {
    name: 'change-indexer-row',
    components: {
        AppLink,
        SelectIndexer,
        StateSwitch
    },
    props: {
        show: Object
    },
    data() {
        return {
            // Keep track of the manual searched/selected show.
            currentShow: this.show,
            searchedShow: {
                searched: false,
                indexer: null,
                id: null
            },
            displaySearch: false,
            searchComponent: null,
            state: false
        };
    },
    computed: {
        ...mapState({
            queueitems: state => state.shows.queueitems
        }),
        ...mapGetters(['indexerIdToName'])
    },
    methods: {
        selectIndexerChange({ text, value }) {
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

            // Bind the 'selected' event to the searchComponent vm.
            this.searchComponent.$on('selected', ({ result }) => {
                this.searchedShow.searched = true;
                this.searchedShow.indexer = indexerIdToName(result.indexerId);
                this.searchedShow.id = result.showId;

                // Emit the event
                this.$emit('selected', { show, indexer: this.searchedShow.indexer, showId: this.searchedShow.id });
            });

            // Bind the 'close' event to the searchComponent vm.
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
        }
    },
    watch: {
        queueitems(queueItem) {
            const { show } = this;
            if (!('changeStatus' in show)) {
                return;
            }
            const foundItem = queueItem.find(item => item.identifier === show.changeStatus.identifier);
            if (foundItem) {
                // Update the steps
                Vue.set(show.changeStatus, 'steps', foundItem.step);
                if (foundItem.inProgress) {
                    this.state = 'loading';
                }
                if (foundItem.success !== null) {
                    this.state = 'yes';
                }
            }
        }
    }
};
</script>
<style scoped>
.step-container {
    position: relative;
}

.stepdisplay {
    display: none;
    position: absolute;
    background-color: rgb(95, 95, 95);
    font-size: 14px;
    border: 1px solid rgb(125, 125, 125);
    z-index: 1;
    width: auto;
    white-space: nowrap;
    right: 20px;
    top: 0;
}

.stepdisplay ul {
    padding: 2px 5px 2px 5px;
}

.stepdisplay li {
    list-style-type: none;
    text-align: left;
}

.step-container .state:hover + .stepdisplay {
    display: block;
}

tr:hover {
    background-color: rgb(145, 145, 145);
}
</style>
