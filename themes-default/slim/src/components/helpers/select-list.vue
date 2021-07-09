<template>
    <div class="select-list max-width" v-bind="{disabled}">
        <i class="switch-input glyphicon glyphicon-refresh" @click="switchFields()" title="Switch between a list and comma separated values" />

        <ul v-if="!csvMode">
            <li v-for="item of editItems" :key="item.id">
                <div class="input-group">
                    <input disabled class="form-control input-sm" type="text" v-model="item.value" @input="removeEmpty(item)">
                    <div class="input-group-btn" @click="deleteItem(item)">
                        <div style="font-size: 14px; background-color: rgb(238, 238, 238);" class="btn btn-default input-sm">
                            <i class="glyphicon glyphicon-remove" title="Remove" />
                        </div>
                    </div>
                </div>
            </li>
            <div class="new-item">
                <div class="input-group">
                    <input class="form-control input-sm" type="text" ref="newItemInput" v-model="newItem" placeholder="add new values per line">
                    <div class="input-group-btn" @click="addNewItem()">
                        <div style="font-size: 14px" class="btn btn-default input-sm">
                            <i class="glyphicon glyphicon-plus" title="Add" />
                        </div>
                    </div>
                </div>
            </div>
            <div v-if="newItem.length > 0" class="new-item-help">
                Click <i class="glyphicon glyphicon-plus" /> to finish adding the value.
            </div>
        </ul>

        <div v-else class="csv">
            <input class="form-control input-sm" type="text" v-model="csv" placeholder="add values comma separated">
        </div>
    </div>
</template>
<script>
export default {
    name: 'select-list',
    props: {
        listItems: {
            type: Array,
            default: () => [],
            required: true
        },
        unique: {
            type: Boolean,
            default: true,
            required: false
        },
        csvEnabled: {
            type: Boolean,
            default: false,
            required: false
        },
        disabled: {
            type: Boolean,
            default: false
        }
    },
    data() {
        return {
            editItems: [],
            newItem: '',
            indexCounter: 0,
            csv: '',
            csvMode: this.csvEnabled
        };
    },
    mounted() {
        this.editItems = this.sanitize(this.listItems);
        this.csv = this.editItems.map(item => item.value).join(', ');
    },
    created() {
        /**
         * ListItems property might receive values originating from the API,
         * that are sometimes not available when rendering.
         * @TODO: This is not ideal! Maybe we can remove this in the future.
         */
        const unwatchProp = this.$watch('listItems', () => {
            unwatchProp();

            this.editItems = this.sanitize(this.listItems);
            this.csv = this.editItems.map(item => item.value).join(', ');
        });
    },
    methods: {
        addItem(item) {
            if (this.unique && this.editItems.find(i => i.value === item)) {
                return;
            }
            this.editItems.push({ id: this.indexCounter, value: item });
            this.indexCounter += 1;
        },
        addNewItem() {
            const { newItem, editItems } = this;
            if (this.newItem === '') {
                return;
            }
            this.addItem(newItem);
            this.newItem = '';
            this.$emit('change', editItems);
        },
        deleteItem(item) {
            this.editItems = this.editItems.filter(e => e !== item);
            this.$refs.newItemInput.focus();
            this.$emit('change', this.editItems);
        },
        removeEmpty(item) {
            return item.value === '' ? this.deleteItem(item) : false;
        },
        /**
         * Initially an array of strings is passed, which we'd like to translate to an array of object.
         * Where the index has been added.
         * @param {string[]} values - Array of strings.
         * @returns {Object[]} - An array of objects with the index and value.
         */
        sanitize(values) {
            if (!values) {
                return [];
            }

            return values.map(value => {
                if (typeof (value) === 'string') {
                    this.indexCounter += 1;
                    return {
                        id: this.indexCounter - 1,
                        value
                    };
                }
                return value;
            });
        },
        /**
         * Depending on which option is selected, sync the data to the other.
         * Sync from editItems to a csv (comma separated) field.
         * Or from csv to editItems.
         */
        syncValues() {
            if (this.csvMode) {
                this.editItems = [];
                this.csv.split(',').forEach((value => {
                    // Omit empty strings
                    if (value.trim()) {
                        this.addItem(value.trim());
                    }
                }));
                this.$emit('change', this.editItems);
            } else {
                this.csv = this.editItems.map(item => item.value).join(', ');
            }
        },
        /**
         * When switching between a list of inputs and a csv input
         * whe're making sure that 1. the data is updated in editItems (which is the source of truth)
         * and this.csv, which keeps track of the csv.
         */
        switchFields() {
            this.syncValues();
            this.csvMode = !this.csvMode;
        }
    },
    watch: {
        csv() {
            this.syncValues();
        },
        listItems() {
            this.editItems = this.sanitize(this.listItems);
            this.newItem = '';
        }
    }
};
</script>
<style scoped>
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

div.select-list input,
div.select-list img {
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
