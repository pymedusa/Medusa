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

    div.select-list input, div.select-list img {
        display: inline-block;
        box-sizing: border-box;
    }

    div.select-list.max-width {
        max-width: 450px;
    }

    div.select-list .switch-input {
        height: 18px;
        width: 18px;
        left: -8px;
        top: 4px;
        position: absolute;
        z-index: 10;
        opacity: 0.6;
    }

</style>
<script type="text/x-template" id="select-list">
    <div class="select-list max-width">
        <img class="switch-input" src="images/refresh.png" @click="switchFields()"/>

        <div class="default" v-if="!csvEnabled">
            <ul>
                <li v-for="item of editItems">
                    <div class="input-group">
                        <input class="form-control input-sm" type="text" v-model="item.value"/>
                        <div class="input-group-btn" @click="deleteItem(item)">
                            <div style="font-size: 14px" class="btn btn-default input-sm">
                                <i class="glyphicon glyphicon-remove"></i>
                            </div>
                        </div>
                    </div>
                </li>
                <div class="new-item">
                    <div class="input-group">
                        <input class="form-control input-sm" type="text" v-model="newItem" placeholder="add new values per line" />
                        <div class="input-group-btn" @click="addNewItem()">
                                <div style="font-size: 14px" class="btn btn-default input-sm">
                                    <i class="glyphicon glyphicon-plus"></i>
                                </div>
                        </div>
                    </div>
                </div>
            </ul>
        </div>

        <div class="csv" v-if="csvEnabled">
            <input class="form-control input-sm" type="text" v-model="csv" placeholder="add values comma separated "/>
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
            required: true
        }
    },
    data() {
        return {
            lock: false,
            editItems: [],
            newItem: '',
            indexCounter: 0,
            csv: '',
            csvEnabled: false,
            csvValid: true
        }
    },
    mounted() {
        this.lock = true;
        this.editItems = this.sanitize(this.listItems);
        this.$nextTick(() => this.lock = false);
        this.csv = this.editItems.map(x => x.value).join(', ');
    },
    methods: {
        addItem: function(item) {
            this.editItems.push({id: this.indexCounter, value: item});
            this.indexCounter += 1;
        },
        addNewItem: function(evt) {
            this.addItem(this.newItem);
            this.newItem = '';
        },
        deleteItem: function(item) {
            this.editItems = this.editItems.filter(e => e !== item);
            this.newItem = item.value;
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
