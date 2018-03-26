<script type="text/x-template" id="file-browser-template">
    <div>
        <input v-model="currentPath" :name="name" type="text" id="episodeDir" class="input-sm form-control form-control-inline fileBrowserField"/> <input v-if="showBrowseButton" type="button" :value="'Browse\u2026'" class="btn btn-inline fileBrowserButton">
        <div class="fileBrowserDialog" style="display:hidden"></div>
        <!-- <file-list files="files"></file-list> -->
        <input @keyup.enter="browse($event.target.value)" :value="currentPath" type="text" class="form-control input-sm fileBrowserSearchBox" style="display: none;"/>
        <ul class="fileBrowserFileList" style="display: hidden;">
            <li v-for="file in files" class="ui-state-default ui-corner-all">
                <a
                    @mouseover="file.isFile ? '' : addClass($event, 'ui-icon-folder-open')"
                    @mouseout="file.isFile ? '' : removeClass($event, 'ui-icon-folder-open')"
                    @click="fileClicked(file)"
                ><span :class="'ui-icon ' + (file.isFile ? 'ui-icon-blank' : 'ui-icon-folder-collapsed')"></span> {{file.name}}</app-link>
            </li>
        </ul>
    </div>
</script>
<script>
Vue.component('file-browser', {
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
            type: Number,
            default: 0
        },
        showBrowseButton: {
            type: Boolean,
            default: true
        },
        // Localstorage key
        // Maybe we should rename?
        key: {
            type: String,
            default: 'path'
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
            files: [],
            currentPath: '',
            lastPath: '',
            defaults: {
                title: 'Choose Directory',
                url: 'browser/',
                autocompleteURL: 'browser/complete',
                includeFiles: 0,
                showBrowseButton: true,
                key: 'path',
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
            event.target.children[0].classList.add(classToAdd);
        },
        removeClass(event, classToRemove) {
            event.target.children[0].classList.remove(classToRemove);
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
                includeFiles
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
            browse(vm.initialDir || vm.currentPath);
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
                        .append('<app-link class="nowrap">' + resultItem + '</app-link>')
                        .appendTo(ul);
                };
            }

            let path;
            let ls = false;
            // If the text field is empty and we're given a key then populate it with the last browsed value from localStorage
            try {
                ls = Boolean(localStorage.getItem);
            } catch (err) {
                console.log(err);
            }
            if (ls && vm.key) {
                path = localStorage['fileBrowser-' + vm.key];
            }
            if (vm.key && vm.currentPath.length === 0 && path) {
                vm.currentPath = path;
            }

            const callback = (path = vm.currentPath) => {
                // Use a localStorage to remember for next time -- no ie6/7
                if (ls && vm.key) {
                    localStorage['fileBrowser-' + vm.key] = path;
                }
            };

            if (options.showBrowseButton) {
                // Append the browse button and give it a click behaviour
                resultField.after(
                    $('.fileBrowserButton').on('click', function() {
                        const initialDir = vm.currentPath || (options.key && path) || '';
                        const optionsWithInitialDir = $.extend({}, options, { initialDir });
                        $(this).nFileBrowser(callback, optionsWithInitialDir);
                        return false;
                    })
                );
            }
            return resultField;
        };

        $(this.$el).children('input').fileBrowser({
            title: this.title,
            key: 'postprocessPath'
        });
    },
    template: `#file-browser-template`
});
</script>
