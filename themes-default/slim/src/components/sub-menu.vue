<template>
    <div v-if="subMenu.length > 0" id="sub-menu-wrapper">
        <div id="sub-menu-container" class="col-md-12 shadow">
            <div id="sub-menu" class="submenu-default hidden-print">
                <app-link
                    v-for="menuItem in subMenu"
                    :key="`sub-menu-${menuItem.title}`"
                    :href="menuItem.path"
                    class="btn-medusa top-5 bottom-5"
                    @[clickEventCond(menuItem)].native.prevent="runMethod($event, menuItem)"
                >
                    <span :class="['pull-left', menuItem.icon]" /> {{ menuItem.title }}
                </app-link>

                <show-selector v-if="showForRoutes" :show-slug="$route.query.showslug" follow-selection />
            </div>
        </div>

        <!-- This fixes some padding issues on screens larger than 1281px -->
        <div class="btn-group" />
    </div>
</template>
<script>
import { mapState, mapActions, mapGetters } from 'vuex';
import { AppLink, ShowSelector } from './helpers';

export default {
    name: 'sub-menu',
    components: {
        AppLink,
        ShowSelector
    },
    computed: {
        ...mapState({
            client: state => state.auth.client
        }),
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
            return this.$route.query.slug;
        },
        showForRoutes() {
            const { $route } = this;
            return ['show', 'editShow'].includes($route.name);
        }
    },
    methods: {
        ...mapActions({
            removeShow: 'removeShow'
        }),
        clickEventCond(menuItem) {
            // If the menu item has properties confirm or method, we want to handle the click by
            // the runMethod() method.
            return menuItem.confirm || menuItem.method ? 'click' : null;
        },
        async runMethod(event, menuItem) {
            const { client } = this;
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

            if (menuItem.confirm === 'removeshow') {
                const { getCurrentShow, removeShow, $router } = this;
                options.title = 'Remove Show';
                options.text = `Are you sure you want to remove <span class="footerhighlight">${getCurrentShow.title}</span> from the database?<br><br>
                                <input type="checkbox" id="deleteFiles"> <span class="red-text">Check to delete files as well. IRREVERSIBLE</span>`;
                options.confirm = async () => {
                    // Already remove show from frontend store + localStorage
                    removeShow(getCurrentShow);

                    const params = { showslug: getCurrentShow.id.slug };
                    if (document.querySelector('#deleteFiles').checked) {
                        params.full = 1;
                    }

                    // Start removal of show in backend
                    await client.apiRoute.get('home/deleteShow', { params });

                    // Navigate back to /home
                    $router.push({ name: 'home', query: undefined });
                };
            } else if (menuItem.confirm === 'clearhistory') {
                options.title = 'Clear History';
                options.text = 'Are you sure you want to clear all download history?';
            } else if (menuItem.confirm === 'trimhistory') {
                options.title = 'Trim History';
                options.text = 'Are you sure you want to trim all download history older than 30 days?';
            } else if (menuItem.confirm === 'submiterrors') {
                options.title = 'Submit Errors';
                options.text = `Are you sure you want to submit these errors?<br><br>
                                <span class="red-text">Make sure Medusa is updated and trigger<br>
                                this error with debug enabled before submitting</span>`;
            } else if (menuItem.method === 'updatekodi') {
                try {
                    await client.api.post('notifications/kodi/update');
                    this.$snotify.success(
                        'Update kodi library',
                        'Success'
                    );
                } catch (error) {
                    this.$snotify.warning(
                        'Error Update kodi library, check your logs',
                        'Warning'
                    );
                }
            } else {
                return;
            }

            if (menuItem.confirm) {
                $.confirm(options, event);
            }
        }
    }
};
</script>
<style scoped>
/* Theme-specific styling adds the rest */
#sub-menu-wrapper {
    position: relative;
    width: 100%;
    z-index: 1;
}

#sub-menu-container {
    min-height: 41px;
    margin-top: 12px;
}

#sub-menu {
    font-size: 12px;
    padding-top: 2px;
    display: inline-block;
    width: 100%;
}

#sub-menu > a {
    float: right;
    margin-left: 4px;
}
</style>
