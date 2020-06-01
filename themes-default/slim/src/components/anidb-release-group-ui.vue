<template>
    <div class="anidb-release-group-ui-wrapper top-10 max-width">
        <template v-if="fetchingGroups">
            <state-switch state="loading" :theme="layout.themeName" />
            <span>Fetching release groups...</span>
        </template>
        <div v-else class="row">
            <div class="col-sm-4 left-whitelist">
                <span>Whitelist</span><img v-if="showDeleteFromWhitelist" class="deleteFromWhitelist" src="images/no16.png" @click="deleteFromList('whitelist')">
                <ul>
                    <li @click="release.toggled = !release.toggled" v-for="release in itemsWhitelist" :key="release.id" :class="{active: release.toggled}">{{ release.name }}</li>
                    <div class="arrow" @click="moveToList('whitelist')">
                        <img src="images/curved-arrow-left.png">
                    </div>
                </ul>
            </div>
            <div class="col-sm-4 center-available">
                <span>Release groups</span>
                <ul>
                    <li v-for="release in itemsReleaseGroups" :key="release.id" class="initial" :class="{active: release.toggled}" @click="release.toggled = !release.toggled">{{ release.name }}</li>
                    <div class="arrow" @click="moveToList('releasegroups')">
                        <img src="images/curved-arrow-left.png">
                    </div>
                </ul>
            </div>
            <div class="col-sm-4 right-blacklist">
                <span>Blacklist</span><img v-if="showDeleteFromBlacklist" class="deleteFromBlacklist" src="images/no16.png" @click="deleteFromList('blacklist')">
                <ul>
                    <li @click="release.toggled = !release.toggled" v-for="release in itemsBlacklist" :key="release.id" :class="{active: release.toggled}">{{ release.name }}</li>
                    <div class="arrow" @click="moveToList('blacklist')">
                        <img src="images/curved-arrow-left.png">
                    </div>
                </ul>
            </div>
        </div>
        <div id="add-new-release-group" class="row">
            <div class="col-md-4">
                <input v-model="newGroup" class="form-control input-sm" type="text" placeholder="add custom group">
            </div>
            <div class="col-md-8">
                <p>Use the input to add custom whitelist / blacklist release groups. Click on the <img src="images/curved-arrow-left.png"> to add it to the correct list.</p>
            </div>
        </div>
    </div>
</template>

<script>
import { mapState } from 'vuex';

import { apiRoute } from '../api';
import { StateSwitch } from './helpers';

export default {
    name: 'anidb-release-group-ui',
    components: {
        StateSwitch
    },
    props: {
        showName: {
            type: String,
            required: true
        },
        blacklist: {
            type: Array,
            default: () => []
        },
        whitelist: {
            type: Array,
            default: () => []
        }
    },
    data() {
        return {
            index: 0,
            allReleaseGroups: [],
            newGroup: '',
            fetchingGroups: false,
            remoteGroups: []
        };
    },
    mounted() {
        this.createIndexedObjects(this.blacklist, 'blacklist');
        this.createIndexedObjects(this.whitelist, 'whitelist');
        this.createIndexedObjects(this.remoteGroups, 'releasegroups');

        this.fetchGroups();
    },
    methods: {
        async fetchGroups() {
            const { showName } = this;
            if (!showName) {
                return;
            }

            this.fetchingGroups = true;
            console.log('Fetching release groups');

            const params = {
                series_name: showName // eslint-disable-line camelcase
            };

            try {
                const { data } = await apiRoute.get('home/fetch_releasegroups', { params, timeout: 30000 });
                if (data.result !== 'success') {
                    throw new Error('Failed to get release groups, check server logs for errors.');
                }
                this.remoteGroups = data.groups || [];
            } catch (error) {
                const message = `Error while trying to fetch release groups for show "${showName}": ${error || 'Unknown'}`;
                this.$snotify.warning(message, 'Error');
                console.error(message);
            } finally {
                this.fetchingGroups = false;
            }
        },
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

                if (this.allReleaseGroups.filter(group => group.name === itemAsObject.name && group.memberOf === list).length === 0) {
                    this.allReleaseGroups.push(itemAsObject);
                    this.index += 1; // Increment the counter for our next item.
                }
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
        ...mapState({
            layout: state => state.config.layout
        }),
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
        showName() {
            this.fetchGroups();
        },
        allReleaseGroups: {
            deep: true,
            handler(items) {
                const groupNames = {
                    whitelist: [],
                    blacklist: []
                };

                items.forEach(item => {
                    if (Object.keys(groupNames).includes(item.memberOf)) {
                        groupNames[item.memberOf].push(item.name);
                    }
                });

                this.$emit('change', groupNames);
            }
        },
        remoteGroups(newGroups) {
            this.createIndexedObjects(newGroups, 'releasegroups');
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
