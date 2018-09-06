<script type="text/x-template" id="sub-menu-template">
<div id="sub-menu-wrapper">
    <div id="sub-menu-container" class="row shadow">
        <div id="sub-menu" class="submenu-default hidden-print col-md-12">
            <template v-for="menuItem in subMenu">
                <app-link v-if="!menuItem.confirm" :key="menuItem.title" :href="menuItem.path" class="btn-medusa top-5 bottom-5">
                    <span :class="['pull-left', menuItem.icon]"></span> {{ menuItem.title }}
                </app-link>
                <app-link v-else :key="menuItem.title" :href="menuItem.path" class="btn-medusa top-5 bottom-5" @click.native.prevent="confirmDialog($event, menuItem.class)">
                    <span :class="['pull-left', menuItem.icon]"></span> {{ menuItem.title }}
                </app-link>
            </template>

            <show-selector v-if="showSelectorVisible" :show-slug="curShowSlug"></show-selector>
        </div>
    </div>

    <!-- This fixes some padding issues on screens larger than 1281px -->
    <div class="btn-group"></div>
</div>
</script>
<%!
    import json
%>
<script>
const SubMenuComponent = {
    name: 'sub-menu',
    template: '#sub-menu-template',
    data() {
        return {
            // Python conversions
            // @TODO: Add the submenu definitions to VueRouter's routes object
            rawSubMenu: ${json.dumps(submenu)}
        };
    },
    computed: {
        subMenu() {
            return this.rawSubMenu.filter(item => item.requires === undefined || item.requires);
        },
        showSelectorVisible() {
            const { pathname } = window.location;
            return pathname.includes('/home/displayShow');
        },
        curShowSlug() {
            if (!this.showSelectorVisible) {
                return null;
            }
            const { params } = this;
            const { indexername, seriesid } = params;
            if (indexername && seriesid) {
                return indexername + seriesid;
            }
            return '';
        },
        params() {
            const { search } = window.location;
            return search.slice(1).split('&').reduce((obj, pair) => {
                const [key, value] = pair.split('=');
                obj[key] = value;
                return obj;
            }, {});
        }
    },
    methods: {
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
                const showName = document.querySelector('#showtitle').dataset.showname;
                options.title = 'Remove Show';
                <%text>
                options.text = `Are you sure you want to remove <span class="footerhighlight">${showName}</span> from the database?<br><br>
                                <input type="checkbox" id="deleteFiles"> <span class="red-text">Check to delete files as well. IRREVERSIBLE</span>`;
                </%text>
                options.confirm = $element => {
                    window.location.href = $element[0].href + (document.getElementById('deleteFiles').checked ? '&full=1' : '');
                };
            } else if (action === 'clearhistory') {
                options.title = 'Clear History';
                options.text = 'Are you sure you want to clear all download history?';
            } else if (action === 'trimhistory') {
                options.title = 'Trim History';
                options.text = 'Are you sure you want to trim all download history older than 30 days?';
            } else if (action === 'submiterrors') {
                options.title = 'Submit Errors';
                options.text =  `Are you sure you want to submit these errors?<br><br>
                                 <span class="red-text">Make sure Medusa is updated and trigger<br>
                                 this error with debug enabled before submitting</span>`;
            } else {
                return;
            }

            $.confirm(options, event);
        }
    }
};

window.components.push(SubMenuComponent);
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
</style>
