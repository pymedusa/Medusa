<template>
    <div class="sorted-select-list max-width" v-bind="{disabled}">
        <draggable
            tag="ul"
            v-model="editItems"
            class="list-group"
            handle=".handle"
            @start="dragging = true"
            @end="dragging = false"
        >
            <li v-for="item of editItems" :key="item.id" class="draggable-list">
                <font-awesome-icon :icon="'align-justify'" class="handle" />
                <div class="draggable-input-group">
                    <input class="form-control input-sm" type="text" v-model="item.value" @input="removeEmpty(item)">
                    <div class="input-group-btn" @click="deleteItem(item)">
                        <div style="font-size: 14px" class="btn btn-default input-sm">
                            <i class="glyphicon glyphicon-remove" title="Remove" />
                        </div>
                    </div>
                </div>
            </li>
        </draggable>
        <div class="new-item">
            <div class="draggable-input-group">
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
    </div>
</template>
<script>
import Draggable from 'vuedraggable';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';

export default {
    name: 'sorted-select-list',
    components: { Draggable, FontAwesomeIcon },
    props: {
        listItems: {
            type: Array,
            default: () => [],
            required: true
        },
        unique: {
            type: Boolean,
            default: true
        },
        disabled: Boolean,
        sorted: Boolean
    },
    data() {
        return {
            editItems: [],
            newItem: '',
            indexCounter: 0,
            dragging: false
        };
    },
    mounted() {
        this.editItems = this.sanitize(this.listItems);
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
        }
    },
    watch: {
        listItems() {
            this.editItems = this.sanitize(this.listItems);
            this.newItem = '';
        },
        dragging(value) {
            const { editItems } = this;
            if (!value) {
                this.$emit('change', editItems);
            }
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

.draggable-list {
    list-style: none;
}

.draggable-input-group {
    display: inline-flex;
    width: 300px;
}
</style>
