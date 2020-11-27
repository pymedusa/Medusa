<template>
    <div v-if="subMenu.length > 0" id="sub-menu-wrapper" class="row">
        <div id="sub-menu-container" class="col-md-12 shadow">
            <div id="sub-menu" class="submenu-default hidden-print">
                <app-link
                    v-for="menuItem in subMenu"
                    :key="`sub-menu-${menuItem.title}`"
                    :href="menuItem.path"
                    class="btn-medusa top-5 bottom-5"
                    @[clickEventCond(menuItem)].native.prevent="confirmDialog($event, menuItem.confirm)"
                >
                    <span :class="['pull-left', menuItem.icon]" /> {{ menuItem.title }}
                </app-link>

                <show-selector v-if="showForRoutes" :show-slug="curShowSlug" follow-selection />
            </div>
        </div>

        <!-- This fixes some padding issues on screens larger than 1281px -->
        <div class="btn-group" />
    </div>
</template>
<script>
import { mapGetters } from 'vuex';
import { AppLink, ShowSelector } from './helpers';

export default {
    name: 'sub-menu',
    components: {
        AppLink,
        ShowSelector
    },
    computed: {
        ...mapGetters({
            getCurrentShow: 'getCurrentShow'
        }),
        subMenu() {
            const { $route } = this;
            let subMenu = $route.meta.subMenu || [];
            if (typeof subMenu === 'function') {
                subMenu = subMenu(this);
            }
            // Filters `requires = false` and reverses the array
            const reducer = (arr, item) => (item.requires === undefined || item.requires) ? arr.concat(item) : arr;
            return subMenu.reduceRight(reducer, []);
        },
        curShowSlug() {
            const { $route } = this;
            const { indexername, seriesid } = $route.query;
            if (indexername && seriesid) {
                return indexername + seriesid;
            }
            return '';
        },
        showForRoutes() {
            const { $route } = this;
            return ['show', 'editShow'].includes($route.name);
        }
    },
    methods: {
        clickEventCond(menuItem) {
            return menuItem.confirm ? 'click' : null;
        },
        confirmDialog(event, action) {
            const options = {
                confirmButton: 'Yes',
                cancelButton: 'Cancel',
                dialogClass: 'modal-dialog',
                post: false,
                button: $(event.currentTarget),
                confirm($element) {
                    window.location.href = $element[0].href;
                }
            };

            if (action === 'removeshow') {
                const { getCurrentShow } = this;
                options.title = 'Remove Show';
                options.text = `Are you sure you want to remove <span class="footerhighlight">${getCurrentShow.title}</span> from the database?<br><br>
                                <input type="checkbox" id="deleteFiles"> <span class="red-text">Check to delete files as well. IRREVERSIBLE</span>`;
                options.confirm = $element => {
                    window.location.href = $element[0].href + (document.querySelector('#deleteFiles').checked ? '&full=1' : '');
                };
            } else if (action === 'clearhistory') {
                options.title = 'Clear History';
                options.text = 'Are you sure you want to clear all download history?';
            } else if (action === 'trimhistory') {
                options.title = 'Trim History';
                options.text = 'Are you sure you want to trim all download history older than 30 days?';
            } else if (action === 'submiterrors') {
                options.title = 'Submit Errors';
                options.text = `Are you sure you want to submit these errors?<br><br>
                                <span class="red-text">Make sure Medusa is updated and trigger<br>
                                this error with debug enabled before submitting</span>`;
            } else {
                return;
            }

            $.confirm(options, event);
        }
    }
};
</script>
<style scoped>
/* Theme-specific styling adds the rest */
#sub-menu-container {
    z-index: 550;
    min-height: 41px;
}

#sub-menu {
    font-size: 12px;
    padding-top: 2px;
}

#sub-menu > a {
    float: right;
    margin-left: 4px;
}

@media (min-width: 1281px) {
    #sub-menu-container {
        position: fixed;
        width: 100%;
        top: 51px;
    }
}

@media (max-width: 1281px) {
    #sub-menu-container {
        position: relative;
        margin-top: -24px;
    }
}

@media (max-width: 767px) {
    #sub-menu-wrapper {
        display: flex;
    }
}
</style>
