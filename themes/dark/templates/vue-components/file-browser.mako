<style scoped>
    /* =========================================================================
    Style for the file-browser.mako.
    Should be moved from here, when moving the .vue files.
    ========================================================================== */
    div.file-browser.max-width {
        max-width: 450px;
    }
    div.file-browser .input-group-no-btn {
        display: flex;
    }
</style>
<script type="text/x-template" id="file-browser">
    <div class="file-browser max-width">
        <div :class="(showBrowseButton ? 'input-group' : 'input-group-no-btn')">
            <input ref="locationInput" v-model="currentPath" :name="name" type="text" class="form-control input-sm fileBrowserField"/>
            <div v-if="showBrowseButton" @click.prevent="openDialog" class="input-group-btn" :title="title" :alt="title">
                <div style="font-size: 14px" class="btn btn-default input-sm">
                    <i class="glyphicon glyphicon-open"></i>
                </div>
            </div>
        </div>

        <div ref="fileBrowserDialog" class="fileBrowserDialog" style="display: none;"></div>
        <input ref="fileBrowserSearchBox" @keyup.enter="browse($event.target.value)" :value="currentPath" type="text" class="form-control" style="display: none;"/>
        <ul ref="fileBrowserFileList" style="display: none;">
            <li v-for="file in files" class="ui-state-default ui-corner-all">
                <a @mouseover="toggleFolder(file, $event)" @mouseout="toggleFolder(file, $event)" @click="fileClicked(file)">
                    <span :class="'ui-icon ' + (file.isFile ? 'ui-icon-blank' : 'ui-icon-folder-collapsed')"></span> {{file.name}}
                </a>
            </li>
        </ul>
    </div>
</script>
<script>
const fileBrowserComponent = {
    name: 'file-browser',
    template: '#file-browser',
    props: {
        // Used for form submission
        name: {
            type: String,
            default: 'proc_dir'
        },
        // Title for the dialog and the browse button
        title: {
            type: String,
            default: 'Choose Directory'
        },
        includeFiles: {
            type: Boolean,
            default: false
        },
        showBrowseButton: {
            type: Boolean,
            default: true
        },
        // Enable autocomplete on the input field
        autocomplete: {
            type: Boolean,
            default: false
        },
        localStorageKey: {
            type: String,
            default: ''
        },
        initialDir: {
            type: String,
            default: ''
        }
    },
    data() {
        const testLocalStorage = () => {
            try {
                Boolean(localStorage.getItem);
                return true;
            } catch (err) {
                console.log(err);
                return false;
            }
        };

        return {
            lock: false,
            unwatchProp: null,

            files: [],
            currentPath: this.initialDir,
            lastPath: '',
            url: 'browser/',
            autocompleteUrl: 'browser/complete',
            fileBrowserDialog: null,
            localStorageSupport: testLocalStorage()
        };
    },
    created() {
        /**
         * initialDir property might receive values originating from the API,
         * that are sometimes not avaiable when rendering.
         * @TODO: Maybe we can remove this in the future.
         */
        this.unwatchProp = this.$watch('initialDir', (newValue, oldValue) => {
            this.unwatchProp();

            this.lock = true;
            this.currentPath = newValue;
            this.$nextTick(() => this.lock = false);
        });
    },
    mounted() {
        // Initialize the fileBrowser.
        const { autocomplete, fileBrowser, storedPath, $refs } = this;
        fileBrowser($refs.locationInput, autocomplete)
            .on('autocompleteselect', (event, ui) => {
                this.currentPath = ui.item.value;
            });

        // If the text field is empty and we have the last browsed path, use it
        if (!this.currentPath && storedPath) {
            this.currentPath = storedPath;
        }
    },
    computed: {
        storedPath: {
            // Interact with localStorage, if applicable
            get() {
                const { localStorageSupport, localStorageKey } = this;
                if (!localStorageSupport || !localStorageKey) return null;

                return localStorage['fileBrowser-' + localStorageKey];
            },
            set(newPath) {
                const { localStorageSupport, localStorageKey } = this;
                if (!localStorageSupport || !localStorageKey) return;

                localStorage['fileBrowser-' + localStorageKey] = newPath;
            }
        }
    },
    methods: {
        toggleFolder(file, event) {
            if (file.isFile) return;
            const target = event.target.children[0] || event.target;
            target.classList.toggle('ui-icon-folder-open');
            target.classList.toggle('ui-icon-folder-collapsed');
        },
        fileClicked(file) {
            // If item clicked is file then open file and select "ok"
            // Otherwise browse to dir
            if (file.isFile) {
                this.currentPath = file.path;
                $(this.$el).find('.browserDialog .ui-button:contains("Ok")').click();
            } else {
                this.browse(file.path);
            }
        },
        // ====================================================================
        async browse(path) {
            const { url, includeFiles, fileBrowserDialog } = this;

            // Close autocomplete (needed when clicking enter)
            $(this.$refs.fileBrowserSearchBox).autocomplete('close');

            console.debug('Browsing to ' + path);

            fileBrowserDialog.dialog('option', 'dialogClass', 'browserDialog busy');
            fileBrowserDialog.dialog('option', 'closeText', ''); // This removes the "Close" text

            const data = await $.getJSON(url, {
                path,
                includeFiles: Number(includeFiles)
            });

            this.currentPath = data.shift().currentPath;
            this.files = data;
            fileBrowserDialog.dialog('option', 'dialogClass', 'browserDialog');
        },
        openFileBrowser(callback) {
            const vm = this;
            const { browse, title, fileBrowser, $refs } = vm;
            const { fileBrowserSearchBox, fileBrowserFileList } = $refs;

            if (!vm.fileBrowserDialog) {
                // Make a fileBrowserDialog object if one doesn't exist already
                // set up the jquery dialog
                vm.fileBrowserDialog = $($refs.fileBrowserDialog).dialog({
                    dialogClass: 'browserDialog',
                    title,
                    position: {
                        my: 'center top',
                        at: 'center top+100',
                        of: window
                    },
                    minWidth: Math.min($(document).width() - 80, 650),
                    height: Math.min($(document).height() - 120, $(window).height() - 120),
                    maxHeight: Math.min($(document).height() - 120, $(window).height() - 120),
                    maxWidth: $(document).width() - 80,
                    modal: true,
                    autoOpen: false
                });

                fileBrowserSearchBox.removeAttribute('style');
                vm.fileBrowserDialog // jQuery object
                    .append(fileBrowserSearchBox);
                fileBrowser(fileBrowserSearchBox, true)
                    .on('autocompleteselect', (event, ui) => {
                        browse(ui.item.value);
                    });
            }

            vm.fileBrowserDialog.dialog('option', 'buttons', [{
                text: 'Ok',
                class: 'medusa-btn',
                click() {
                    // Store the browsed path to the associated text field
                    callback(vm.currentPath);
                    $(this).dialog('close');
                }
            }, {
                text: 'Cancel',
                class: 'medusa-btn',
                click() {
                    // Reset currentPath to path before dialog opened
                    vm.currentPath = vm.lastPath;
                    $(this).dialog('close');
                }
            }]);

            vm.fileBrowserDialog.dialog('open');
            browse(vm.currentPath);
            // Set lastPath so we can reset currentPath if we cancel dialog
            vm.lastPath = vm.currentPath;

            fileBrowserFileList.removeAttribute('style');
            vm.fileBrowserDialog // jQuery object
                .append(fileBrowserFileList);
        },
        fileBrowser(target, autocomplete) {
            const vm = this;
            const { autocompleteUrl, includeFiles } = vm;

            // Text field used for the result
            const resultField = $(target);

            if (autocomplete && resultField.autocomplete && autocompleteUrl) {
                let query = '';
                resultField.autocomplete({
                    position: {
                        my: 'top',
                        at: 'bottom',
                        collision: 'flipfit'
                    },
                    source(request, response) {
                        // Keep track of user submitted search term
                        query = $.ui.autocomplete.escapeRegex(request.term);
                        request.includeFiles = Number(includeFiles);
                        $.ajax({
                            url: autocompleteUrl,
                            data: request,
                            dataType: 'json'
                        }).done(data => {
                            // Implement a startsWith filter for the results
                            const matcher = new RegExp('^' + query, 'i');
                            const a = $.grep(data, item => {
                                return matcher.test(item);
                            });
                            response(a);
                        });
                    },
                    open() {
                        $(vm.$el).find('.ui-autocomplete li.ui-menu-item a').removeClass('ui-corner-all');
                    }
                }).data('ui-autocomplete')._renderItem = (ul, item) => {
                    // Highlight the matched search term from the item -- note that this is global and will match anywhere
                    let resultItem = item.label;
                    const x = new RegExp('(?![^&;]+;)(?!<[^<>]*)(' + query + ')(?![^<>]*>)(?![^&;]+;)', 'gi');
                    resultItem = resultItem.replace(x, fullMatch => {
                        return '<b>' + fullMatch + '</b>';
                    });
                    return $('<li></li>')
                        .data('ui-autocomplete-item', item)
                        .append('<a class="nowrap">' + resultItem + '</a>')
                        .appendTo(ul);
                };
            }
            // Returns: jQuery element
            return resultField;
        },
        openDialog() {
            const { openFileBrowser, currentPath } = this;
            openFileBrowser(path => {
                // Store the path to remember for next time -- no ie6/7
                this.storedPath = path || currentPath;
            });
        }
    },
    watch: {
        currentPath(newValue, oldValue) {
            if (!this.lock) {
                this.$emit('update', this.currentPath);
            }
        }
    }
};

Vue.component('file-browser', fileBrowserComponent);
window.components.push(fileBrowserComponent);
</script>
