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
</style>
<script type="text/x-template" id="select-list">
    <div class="select-list">
            <ul>
            <li v-for="item of editItems">
                <input style="display: inline-block" type="text" @change="sendValues" v-model="item.value"/>
                <img style="display: inline-block" src="images/no16.png" alt="N" width="16" height="16" @click="deleteItem(item)">
            </li>
            <div class="new-item">
                <input style="display: inline-block" type="text" v-model="newItem"/>
                <img style="display: inline-block" src="images/pencil_add.png" alt="N" width="16" height="16" @click="addItem">
            </div>
    </div>
</script>
<script>
    // register the component
    Vue.component('select-list', {
        name: 'select-list',
        template: `#select-list`,
        props: ['listItems'],
        mounted() {
            this.editItems = this.sanitize(this.listItems);
        },
        data: function() {
            return {
                editItems: [],
                newItem: '',
                indexCounter: 0
            }
        },
        methods: {
            sendValues: function() {
                this.$emit('change', this.editItems);
            },
            addItem: function(evt) {
                this.editItems.push({id: this.indexCounter, value: this.newItem});
                this.indexCounter += 1;
                this.newItem = '';
                this.sendValues();
            },
            deleteItem: function(item) {
                this.editItems = this.editItems.filter(e => e !== item);
                this.newItem = item.value;
                this.sendValues();
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
            }
        }
    });
</script>
