<style scoped>
    /* =========================================================================
    Style for the file-browser.mako.
    Should be moved from here, when moving the .vue files.
    ========================================================================== */


    div.file-browser.max-width {
        max-width: 450px;
    }

</style>
<script type="text/x-template" id="file-browser">
    <div class="file-browser max-width">
        <div class="input-group">
            <input v-model="currentPath" ref="locationInput" :name="name" type="text" class="form-control input-sm fileBrowserField"/>
            <div class="input-group-btn fileBrowserButton" :title="title" :alt="title">
                <div style="font-size: 14px" class="btn btn-default input-sm">
                    <i class="glyphicon glyphicon-open"></i>
                </div>
            </div>
        </div>

        <div class="fileBrowserDialog" style="display: none;"></div>
        <input @keyup.enter="browse($event.target.value)" :value="currentPath" type="text" class="form-control fileBrowserSearchBox" style="display: none;"/>
        <ul class="fileBrowserFileList" style="display: none;">
            <li v-for="file in files" class="ui-state-default ui-corner-all">
                <a
                    @mouseover="file.isFile ? '' : addClass($event, 'ui-icon-folder-open')"
                    @mouseout="file.isFile ? '' : removeClass($event, 'ui-icon-folder-open')"
                    @click="fileClicked(file)"
                >
                    <span :class="'ui-icon ' + (file.isFile ? 'ui-icon-blank' : 'ui-icon-folder-collapsed')"></span> {{file.name}}
                </a>
            </li>
        </ul>
    </div>
</script>
<script>
Vue.component('file-browser', {
    name: 'file-browser',
    template: `#file-browser`,
    props: {
        title: {
            type: String,
            default: 'Choose Directory'
        },
        url: {
            type: String,
            default: 'browser/'
        },
        autocompleteURL: {
            type: String,
            default: 'browser/complete'
        },
        includeFiles: {
            type: Boolean,
            default: false
        },
        showBrowseButton: {
            type: Boolean,
            default: true
        },
        localStorageKey: {
            type: String,
            default: ''
        },
        initialDir: {
            type: String,
            default: ''
        },
        // Used for form submission
        name: {
            type: String,
            default: 'proc_dir'
        }
    },
    data() {
        return {
            lock: false,
            files: [],
            currentPath: '',
            lastPath: '',
            defaults: {
                title: 'Choose Directory',
                url: 'browser/',
                autocompleteURL: 'browser/complete',
                includeFiles: false,
                showBrowseButton: true,
                localStorageKey: '',
                initialDir: ''
            },
            browse: null
        };
    },
    computed: {
        options() {
            return Object.keys(this.$options.props).reduce((acc, key) => Object.assign(acc, this[key] !== undefined ? { [key]: this[key] } : {}), {});
        }
    },
    methods: {
        addClass(event, classToAdd) {
            // If the cursor is on the <span>, it doesn't work.
            target = event.target.children[0] || event.target;
            target.classList.add(classToAdd);
        },
        removeClass(event, classToRemove) {
            // If the cursor is on the <span>, it doesn't work.
            target = event.target.children[0] || event.target;
            target.classList.remove(classToRemove);
        },
        fileClicked(file) {
            // If item clicked is file then open file and select "ok"
            // Otherwise browse to dir
            if (file.isFile) {
                this.currentPath = file.path;
                $('.browserDialog .ui-button:contains("Ok")').click();
            } else {
                this.browse(file.path);
            }
        }
    },
    mounted() {
        const vm = this;

        let fileBrowserDialog;

        this.browse = async (path, url = this.url, includeFiles = this.includeFiles) => {
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
        };

        $.fn.nFileBrowser = function(callback, options) {
            const {browse} = vm;
            options = Object.assign({}, vm.defaults, options);

            if (fileBrowserDialog) {
                // The title may change, even if fileBrowserDialog already exists
                fileBrowserDialog.dialog('option', 'title', options.title);
            } else {
                // Make a fileBrowserDialog object if one doesn't exist already
                // set up the jquery dialog
                fileBrowserDialog = $('.fileBrowserDialog').dialog({
                    dialogClass: 'browserDialog',
                    title: options.title,
                    position: {
                        my: 'center top',
                        at: 'center top+60',
                        of: window
                    },
                    minWidth: Math.min($(document).width() - 80, 650),
                    height: Math.min($(document).height() - 80, $(window).height() - 80),
                    maxHeight: Math.min($(document).height() - 80, $(window).height() - 80),
                    maxWidth: $(document).width() - 80,
                    modal: true,
                    autoOpen: false
                });

                $('.fileBrowserSearchBox')
                    .removeAttr('style')
                    .appendTo(fileBrowserDialog)
                    .fileBrowser({ showBrowseButton: false })
                    .on('autocompleteselect', (e, ui) => {
                        browse(ui.item.value);
                    });
            }

            fileBrowserDialog.dialog('option', 'buttons', [{
                text: 'Ok',
                class: 'btn',
                click() {
                    // Store the browsed path to the associated text field
                    callback(vm.currentPath);
                    $(this).dialog('close');
                }
            }, {
                text: 'Cancel',
                class: 'btn',
                click() {
                    // Reset currentPath to path before dialog opened
                    vm.currentPath = vm.lastPath;
                    $(this).dialog('close');
                }
            }]);

            fileBrowserDialog.dialog('open');
            browse(vm.currentPath || vm.initialDir);
            // Set lastPath so we can reset currentPath if we cancel dialog
            vm.lastPath = vm.currentPath;

            const list = $('.fileBrowserFileList').removeAttr('style').appendTo(fileBrowserDialog);

            return false;
        };

        $.fn.fileBrowser = function(options) {
            options = Object.assign({}, vm.defaults, options);
            // Text field used for the result
            const resultField = $(this);

            if (resultField.autocomplete && options.autocompleteURL) {
                let query = '';
                resultField.autocomplete({
                    position: {
                        my: 'top',
                        at: 'bottom',
                        collision: 'flipfit'
                    },
                    source(request, response) {
                        // Keep track of user submitted search term
                        query = $.ui.autocomplete.escapeRegex(request.term, options.includeFiles);
                        $.ajax({
                            url: options.autocompleteURL,
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
                        $('.ui-autocomplete li.ui-menu-item a').removeClass('ui-corner-all');
                    }
                }).data('ui-autocomplete')._renderItem = function(ul, item) {
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

            let path;
            let ls = false;
            // If the text field is empty and we're given a localStorageKey then populate it with the last browsed value from localStorage
            try {
                ls = Boolean(localStorage.getItem);
            } catch (err) {
                console.log(err);
            }
            if (ls && vm.localStorageKey) {
                path = localStorage['fileBrowser-' + vm.localStorageKey];
            }
            if (vm.localStorageKey && vm.currentPath.length === 0 && path) {
                vm.currentPath = path;
            }

            const callback = (path = vm.currentPath) => {
                // Use a localStorage to remember for next time -- no ie6/7
                if (ls && vm.localStorageKey) {
                    localStorage['fileBrowser-' + vm.localStorageKey] = path;
                }
            };

            if (options.showBrowseButton) {
                // Append the browse button and give it a click behaviour
                resultField.after(
                    $('.fileBrowserButton').on('click', function() {
                        const initialDir = vm.currentPath || (options.localStorageKey && path) || '';
                        const optionsWithInitialDir = $.extend({}, options, { initialDir });
                        $(this).nFileBrowser(callback, optionsWithInitialDir);
                        return false;
                    })
                );
            }
            return resultField;
        };

        const { title, localStorageKey } = this;
        $(this.$refs.locationInput).fileBrowser({
            title: title,
            localStorageKey: localStorageKey
        }).on('autocompleteselect', (e, ui) => {
            this.currentPath = ui.item.value;
        });
    },
    watch: {
        /**
         * initialDir property might receive values originating from the API,
         * that are sometimes not avaiable when rendering.
         * @TODO: Maybe we can remove this in the future.
         */
        initialDir(newValue, oldValue) {
            this.lock = true;
            this.currentPath = this.currentPath || newValue;
            this.$nextTick(() => this.lock = false);
        },
        currentPath(newValue, oldValue) {
            if (!this.lock) {
                this.$emit('update:location', this.currentPath);
            }
        }
    }
});
</script>
