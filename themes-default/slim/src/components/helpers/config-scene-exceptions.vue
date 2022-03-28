<template>
    <div class="select-list max-width">
        <ul>
            <li v-for="exception of items" :key="`${exception.title}-${exception.season}`">
                <div class="input-group form-inline" :disabled="!exception.custom">
                    <input class="form-control input-sm" type="text" :value="exception.title" :disabled="!exception.custom">

                    <select
                        name="scene-exception-season"
                        class="select-season"
                        v-model="exception.season"
                        :disabled="!exception.custom"
                    >
                        <option v-for="season in availableSeasons" :value="season.value" :key="season.value">
                            {{ season.description }}
                        </option>
                    </select>

                    <div
                        v-if="!exception.custom"
                        class="external-scene-exception"
                        v-tooltip.right="'This exception has been automatically added through an automated process sourcing title aliases from medusa github repo, thexem.de or anidb.info'"
                    >
                        <div class="align-center">
                            <img src="images/ico/favicon-16.png" width="16" height="16" alt="search" title="This exception has been automatically added through an automated process sourcing title aliases from medusa github repo, thexem.de or anidb.info">
                        </div>
                    </div>
                    <div v-else class="input-group-btn" @click="removeException(exception)">
                        <div style="font-size: 14px" class="btn btn-default input-sm">
                            <i class="glyphicon glyphicon-remove" title="Remove" />
                        </div>
                    </div>
                </div>
            </li>

            <div class="new-item">
                <div class="input-group form-inline">
                    <input class="form-control input-sm" type="text" ref="newItemInput" v-model="newItem" placeholder="add new values per line">
                    <select
                        name="add-exception-season"
                        class="select-season"
                        v-model="selectedSeason"
                    >
                        <option v-for="season in availableSeasons" :value="season.value" :key="season.value">
                            {{ season.description }}
                        </option>
                    </select>

                    <div :disabled="!unique" class="input-group-btn" @click="addException()">
                        <div style="font-size: 14px" class="btn btn-default input-sm">
                            <i class="glyphicon glyphicon-plus" title="Add" />
                        </div>
                    </div>
                </div>
            </div>

            <div v-if="!unique">
                <p><b>This exception has already been added for this show.<br>Can't add the same exception twice!</b></p>
            </div>
            <div v-if="newItem.length > 0 && unique" class="new-item-help">
                Click <i class="glyphicon glyphicon-plus" /> to add your <b>{{selectedSeason === -1 ? 'Show Exception' : 'Season Exception' }}</b>.
            </div>
        </ul>
    </div>

</template>
<script>

import { mapActions } from 'vuex';
import { VTooltip } from 'v-tooltip';

export default {
    name: 'config-scene-exceptions',
    directives: {
        tooltip: VTooltip
    },
    props: {
        exceptions: {
            type: Array,
            default: () => []
        },
        show: {
            type: Object,
            default: null
        }
    },
    data() {
        return {
            items: [],
            newItem: '',
            selectedSeason: -1,
            warning: ''
        };
    },
    computed: {
        availableSeasons() {
            const { show } = this;
            const { seasonCount } = show;

            if (!seasonCount) {
                return [];
            }

            const seasons = [];
            seasons.push({ value: -1, description: 'Show Exception' });

            seasons.push(
                ...show.seasonCount.filter(season => season.season !== 0).map(season => {
                    return ({ value: season.season, description: `Season ${season.season}` });
                })
            );

            if (show.config.scene && show.xemNumbering && show.xemNumbering.length > 0) {
                for (const xemNum of show.xemNumbering) {
                    if (xemNum.destination.season === 0) {
                        continue;
                    }

                    if (!seasons.find(s => s.value === xemNum.destination.season)) {
                        seasons.push({ value: xemNum.destination.season, description: `Season ${xemNum.destination.season} (xem)` });
                    }
                }
            }

            return seasons.sort((first, second) => first.value - second.value);
        },
        unique() {
            const { items, newItem } = this;
            return !items.find(exception => exception.title === newItem);
        }
    },
    mounted() {
        const { exceptions } = this;
        this.items = exceptions;
    },
    methods: {
        ...mapActions({
            addSceneException: 'addSceneException',
            removeSceneException: 'removeSceneException'
        }),
        addException() {
            const { addSceneException, clear, selectedSeason, show, newItem, unique } = this;
            if (!unique || newItem === '') {
                return;
            }

            const exception = {
                title: newItem,
                season: selectedSeason,
                custom: true
            };
            addSceneException({ show, exception });
            clear();
        },
        removeException(exception) {
            const { clear, removeSceneException, show } = this;

            removeSceneException({ show, exception });
            clear();
        },
        clear() {
            this.newItem = '';
            this.selectedSeason = -1;
        }
    },
    watch: {
        exceptions(newExceptions) {
            this.items = newExceptions;
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

.form-inline {
    display: contents;
}

.select-season {
    height: 30px;
    padding: 0 3px 0 2px;
}

.select-season[disabled=disabled] {
    background-color: #eee;
}

.external-scene-exception {
    display: table-cell;
    width: 4.5px;
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    background-color: #fff;
    border-color: #ccc;
}

.external-scene-exception div {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 30px;
    border: 1px solid #ccc;
    border-top-left-radius: 0;
    border-top-right-radius: 4px;
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 4px;
    z-index: 2;
    margin-left: -1px;
}

.external-scene-exception > img {
    display: block;
    margin-left: auto;
    margin-right: auto;
}

.external-scene-exception:last-child > .div {
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
}
</style>
