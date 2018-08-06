<template>
    <div class="anidb-release-group-ui-wrapper top-10 max-width">
        <div class="row">
            <div class="col-sm-4 left-whitelist" >
                <span>Whitelist</span><img v-if="showDeleteFromWhitelist" class="deleteFromWhitelist" src="images/no16.png" @click="deleteFromList('whitelist')"/>
                <ul>
                    <li @click="release.toggled = !release.toggled" v-for="release in itemsWhitelist" :key="release.id" :class="{active: release.toggled}">{{ release.name }}</li>
                    <div class="arrow" @click="moveToList('whitelist')">
                        <img src="images/curved-arrow-left.png"/>
                    </div>
                </ul>
            </div>
            <div class="col-sm-4 center-available">
                <span>Release groups</span>
                <ul>
                    <li v-for="release in itemsReleaseGroups" :key="release.id" class="initial" :class="{active: release.toggled}" @click="release.toggled = !release.toggled">{{ release.name }}</li>
                    <div class="arrow" @click="moveToList('releasegroups')">
                        <img src="images/curved-arrow-left.png"/>
                    </div>
                </ul>
            </div>
            <div class="col-sm-4 right-blacklist">
                <span>Blacklist</span><img v-if="showDeleteFromBlacklist" class="deleteFromBlacklist" src="images/no16.png" @click="deleteFromList('blacklist')"/>
                <ul>
                    <li @click="release.toggled = !release.toggled" v-for="release in itemsBlacklist" :key="release.id" :class="{active: release.toggled}">{{ release.name }}</li>
                    <div class="arrow" @click="moveToList('blacklist')">
                        <img src="images/curved-arrow-left.png"/>
                    </div>
                </ul>
            </div>
        </div>
        <div id="add-new-release-group" class="row">
            <div class="col-md-4">
                <input class="form-control input-sm" type="text" v-model="newGroup" placeholder="add custom group"/>
            </div>
            <div class="col-md-8">
                <p>Use the input to add custom whitelist / blacklist release groups. Click on the <img src="images/curved-arrow-left.png"/> to add it to the correct list.</p>
            </div>
        </div>
    </div>
</template>
<script>
import AppLink from './app-link.vue';

module.exports = {
    name: 'anidb-release-group-ui',
    components: {
        AppLink
    },
    props: {
        blacklist: {
            type: Array,
            default() {
                return [];
            }
        },
        whitelist: {
            type: Array,
            default() {
                return [];
            }
        },
        allGroups: {
            type: Array,
            default() {
                return [];
            }
        }
    },
    data() {
        return {
            index: 0,
            allReleaseGroups: [],
            newGroup: ''
        };
    },
    mounted() {
        this.createIndexedObjects(this.blacklist, 'blacklist');
        this.createIndexedObjects(this.whitelist, 'whitelist');
        this.createIndexedObjects(this.allGroups, 'releasegroups');
    },
    methods: {
        toggleItem(release) {
            this.allReleaseGroups = this.allReleaseGroups.map(x => {
                if (x.id === release.id) {
                    x.toggled = !x.toggled;
                }
                return x;
            });
        },
        createIndexedObjects(releaseGroups, list) {
            for (let release of releaseGroups) {
                // Whitelist and blacklist pass an array of strings not objects.
                if (typeof (release) === 'string') {
                    release = { name: release };
                }

                // Merge the passed object with some additional information.
                const itemAsObject = Object.assign({
                    id: this.index,
                    toggled: false, memberOf: list
                }, release);
                this.allReleaseGroups.push(itemAsObject);
                this.index += 1; // Increment the counter for our next item.
            }
        },
        moveToList(list) {
            // Only move items that have been toggled and that are not yet in that list.
            // It's matching them by item.name.
            for (const group of this.allReleaseGroups) {
                const inList = this.allReleaseGroups.find(releaseGroup => {
                    return releaseGroup.memberOf === list && releaseGroup.name === group.name;
                }) !== undefined;

                if (group.toggled && !inList) {
                    group.toggled = false;
                    group.memberOf = list;
                }
            }

            /*
            * Check if there is a value in the custom release group input box,
            * and move this to the selected group (whitelist or blacklist)
            */
            if (this.newGroup && list !== 'releasegroups') {
                this.allReleaseGroups.push({
                    id: this.index,
                    name: this.newGroup,
                    toggled: false,
                    memberOf: list
                });
                this.index += 1;
                this.newGroup = '';
            }
        },
        deleteFromList(list) {
            this.allReleaseGroups = this.allReleaseGroups.filter(x => x.memberOf !== list || !x.toggled);
        }
    },
    computed: {
        itemsWhitelist() {
            return this.allReleaseGroups.filter(x => x.memberOf === 'whitelist');
        },
        itemsBlacklist() {
            return this.allReleaseGroups.filter(x => x.memberOf === 'blacklist');
        },
        itemsReleaseGroups() {
            return this.allReleaseGroups.filter(x => x.memberOf === 'releasegroups');
        },
        showDeleteFromWhitelist() {
            return this.allReleaseGroups
                .filter(x => x.memberOf === 'whitelist' && x.toggled === true)
                .length !== 0;
        },
        showDeleteFromBlacklist() {
            return this.allReleaseGroups
                .filter(x => x.memberOf === 'blacklist' && x.toggled === true)
                .length !== 0;
        }
    },
    watch: {
        allReleaseGroups: {
            handler() {
                this.$emit('change', this.allReleaseGroups);
            },
            deep: true
        }
    }
};
</script>
<style scoped>
div.anidb-release-group-ui-wrapper {
    clear: both;
    margin-bottom: 20px;
}

div.anidb-release-group-ui-wrapper ul {
    border-style: solid;
    border-width: thin;
    padding: 5px 2px 2px 5px;
    list-style: none;
}

div.anidb-release-group-ui-wrapper li.active {
    background-color: cornflowerblue;
}

div.anidb-release-group-ui-wrapper div.arrow img {
    cursor: pointer;
    height: 32px;
    width: 32px;
}

div.anidb-release-group-ui-wrapper img.deleteFromWhitelist,
div.anidb-release-group-ui-wrapper img.deleteFromBlacklist {
    float: right;
}

div.anidb-release-group-ui-wrapper #add-new-release-group p > img {
    height: 16px;
    width: 16px;
    background-color: rgb(204, 204, 204);
}

div.anidb-release-group-ui-wrapper.placeholder {
    height: 32px;
}

div.anidb-release-group-ui-wrapper.max-width {
    max-width: 960px;
}
</style>
