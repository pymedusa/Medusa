<script type="text/x-template" id="anidb-release-group-ui">
    <div id="anidb-release-group-ui-wrapper" class="top-10">
        <link rel="stylesheet" type="text/css" href="css/vue/anidbreleasegroupui.css?${sbPID}" />
        <div class="row">
                <div class="col-sm-4 left-whitelist" >
                    <span>Whitelist</span>
                    <ul>
                        <li @click="toggleItem(item)" v-for="item in itemsWhitelist" v-bind:class="{active: item.toggled}">{{ item.name }}</li>
                        <div class="arrow" @click="moveToList('whitelist')">
                                <img src="images/curved-arrow-left.png"/>
                        </div>
                    </ul>
                </div>
                <div class="col-sm-4 center-available">
                    <span>Release groups</span>
                    <ul>
                        <li v-for="item in itemsReleaseGroups" class="initial " v-bind:class="{active: item.toggled}" @click="toggleItem(item)">{{ item.name }}</li>
                        <div class="arrow" @click="moveToList('releasegroups')">
                            <img src="images/curved-arrow-left.png"/>
                        </div>
                    </ul>
                </div>
                <div class="col-sm-4 right-blacklist">
                    <span>Blacklist</span>
                    <ul>
                        <li @click="toggleItem(item)" v-for="item in itemsBlacklist" v-bind:class="{active: item.toggled}">{{ item.name }}</li>
                        <div class="arrow" @click="moveToList('blacklist')">
                            <img src="images/curved-arrow-left.png"/>
                        </div>
                    </ul>
                </div>
        </div>
        <div id="add-new-release-group">
            <input type="text" v-model="newGroup" />
        </div>
    </div>
</script>
<script>
Vue.component('anidb-release-group-ui', {
    name: 'anidb-release-group-ui',
    template: '#anidb-release-group-ui',
    props: ['series', 'blacklist', 'whitelist', 'allGroups'],
    data() {
        return {
            // JS only
            defSeries: '12345',
            index: 0,
            allItems: [],
            newGroup: ''
        };
    },
    mounted() {
        this.releaseSeries = this.series;
        this.createIndexedObjects(this.blacklist, 'blacklist');
        this.createIndexedObjects(this.whitelist, 'whitelist');
        this.createIndexedObjects(this.allGroups, 'releasegroups');
    },
    methods: {
        sendValues: function() {
            this.$emit('change', this.allItems);
        },
        toggleItem: function(item) {
            this.allItems = this.allItems.map(x => {
                if (x.id === item.id) {
                    x.toggled = !x.toggled;
                }
                return x;
            });
        },
        createIndexedObjects: function(items, list) {
            newList = [];
            for (item of items) {
                itemAsObject = Object.assign({
                    id: this.index, 
                    toggled: false, memberOf: list
                }, item);
                this.allItems.push(itemAsObject);
                this.index += 1;
            }
        },
        moveToList: function(list) {
            for (item of this.allItems) {
                if (item.toggled) {
                    item.toggled = false;
                    item.memberOf = list;
                }
            }

            if (this.newGroup) {
                this.allItems.push({
                    id: this.index,
                    name: this.newGroup, 
                    toggled: false,
                    memberOf: list
                })
                this.index += 1;
                this.newGroup = '';
            }

            this.sendValues();
        }
    },
    computed: {
        itemsWhitelist: function() {
            return this.allItems.filter(x => x.memberOf == 'whitelist');
        },
        itemsBlacklist: function() {
            return this.allItems.filter(x => x.memberOf == 'blacklist');
        },
        itemsReleaseGroups: function() {
            return this.allItems.filter(x => x.memberOf == 'releasegroups');
        }

    }
});
</script>
