<script type="text/x-template" id="select-list">
    <div class="select-list">
            <div v-for="item of editItems">
                <input style="display: inline-block" type="text" @change="sendValues" v-model="item.value"/>
                <img style="display: inline-block" src="images/no16.png" alt="N" width="16" height="16" @click="deleteItem(item)">
            </div>
            <input style="display: inline-block" type="text" v-model="newItem"/>
            <img style="display: inline-block" src="images/pencil_add.png" alt="N" width="16" height="16" @click="addItem">
    </div>
</script>
<script>
    // register the component
    Vue.component('select-list', {
        template: '#select-list',
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
            sanitize: function(items) {
                if (items.filter(item => typeof(item) === 'string').length) {
                    return this.transformToIndexedObject(items);
                } else {
                    return items;
                }
            },
            transformToIndexedObject: arrayOfStrings => {
                arrayOfObjects = [];
                for (let index=0; index < arrayOfStrings.length; index++) {
                    arrayOfObjects.push({id: index, value: arrayOfStrings[index]});
                }
                return arrayOfObjects;
            }
        }
    });
</script>
