<style scoped>
    /* =========================================================================
    Style for the selectList.mako.
    Should be moved from here, when moving the .vue files.
    ========================================================================== */

    div.select-list ul {
        padding-left: 0;
    }

    div.select-list li {
        list-style-type: none;
        display: flex;
    }

    div.select-list .new-item {
        display: flex;
    }

    div.select-list .new-item-help {
        font-weight: bold;
        padding-top: 5px;
    }

    div.select-list input, div.select-list img {
        display: inline-block;
        box-sizing: border-box;
    }

    div.select-list.max-width {
        max-width: 450px;
    }

    div.select-list .switch-input {
        left: -8px;
        top: 4px;
        position: absolute;
        z-index: 10;
        opacity: 0.6;
    }

</style>
<script type="text/x-template" id="select-list">
    <div class="select-list max-width">
        <i class="switch-input glyphicon glyphicon-refresh" @click="switchFields()"
            title="Switch between a list and comma separated values"></i>

        <ul v-if="!csvEnabled">
            <li v-for="item of editItems">
                <div class="input-group">
                    <input class="form-control input-sm" type="text" v-model="item.value" @input="removeEmpty(item)"/>
                    <div class="input-group-btn" @click="deleteItem(item)">
                        <div style="font-size: 14px" class="btn btn-default input-sm">
                            <i class="glyphicon glyphicon-remove" title="Remove"></i>
                        </div>
                    </div>
                </div>
            </li>
            <div class="new-item">
                <div class="input-group">
                    <input class="form-control input-sm" type="text" ref="newItemInput" v-model="newItem" placeholder="add new values per line" />
                    <div class="input-group-btn" @click="addNewItem()">
                        <div style="font-size: 14px" class="btn btn-default input-sm">
                            <i class="glyphicon glyphicon-plus" title="Add"></i>
                        </div>
                    </div>
                </div>
            </div>
            <div v-if="newItem.length > 0" class="new-item-help">
                Click <i class="glyphicon glyphicon-plus"></i> to finish adding the value.
            </div>
        </ul>

        <div v-else class="csv">
            <input class="form-control input-sm" type="text" v-model="csv" placeholder="add values comma separated"/>
        </div>

    </div>
</script>
<script>
// register the component
Vue.component('select-list', {
    name: 'select-list',
    template: '#select-list',
    props: {
        listItems: {
            type: Array,
            default: [],
            required: true
        },
        unique: {
            type: Boolean,
            default: true,
            required: false
        }
    },
    data() {
        return {
            lock: false,
            unwatchProp: null,

            editItems: [],
            newItem: '',
            indexCounter: 0,
            csv: '',
            csvEnabled: false
        }
    },
    created() {
        /**
         * listItems property might receive values originating from the API,
         * that are sometimes not avaiable when rendering.
         * @TODO: Maybe we can remove this in the future.
         */
        this.unwatchProp = this.$watch('listItems', () => {
            this.unwatchProp();

            this.lock = true;
            this.editItems = this.sanitize(this.listItems);
            this.$nextTick(() => this.lock = false);
            this.csv = this.editItems.map(x => x.value).join(', ');
        });
    },
    methods: {
        addItem: function(item) {
            if (this.unique && this.editItems.find(i => i.value === item)) return;
            this.editItems.push({id: this.indexCounter, value: item});
            this.indexCounter += 1;
        },
        addNewItem: function(evt) {
            if (this.newItem === '') return;
            this.addItem(this.newItem);
            this.newItem = '';
        },
        deleteItem: function(item) {
            this.editItems = this.editItems.filter(e => e !== item);
            this.$refs.newItemInput.focus();
        },
        removeEmpty: function(item) {
            return item.value === '' ? this.deleteItem(item) : false;
        },
        /**
         * Initially an array of strings is passed, which we'd like to translate to an array of object.
         * Where the index has been added.
         * @param values - array of strings.
         * @returns - An array of objects with the index and value.
         */
        sanitize: function(values) {
            if (!values) {
                return [];
            }

            return values.map((value, index) => {
                if (typeof(value) === 'string') {
                    return {
                        id: index,
                        value: value
                    }
                } else {
                    return value;
                }
            })
        },
        /**
         * Depending on which option is selected, sync the data to the other.
         * Sync from editItems to a csv (comma separated) field.
         * Or from csv to editItems.
         */
        syncValues: function() {
            if (this.csvEnabled) {
                this.editItems = [];
                this.csv.split(',').forEach((value => {
                    // Omit empty strings
                    if (value.trim()) {
                        this.addItem(value.trim());
                    }
                }));
            } else {
                this.csv = this.editItems.map(x => x.value).join(', ');
            }
        },
        /**
         * When switching between a list of inputs and a csv input
         * whe're making sure that 1. the data is updated in editItems (which is the source of truth)
         * and this.csv, which keeps track of the csv.
         */
        switchFields: function() {
            this.syncValues();
            this.csvEnabled = !this.csvEnabled;
        }
    },
    watch: {
        editItems: {
            handler: function() {
                if (!this.lock) {
                    this.$emit('change', this.editItems);
                }
            },
            deep: true
        },
        csv() {
            this.syncValues();
        }
    }
});
</script>
