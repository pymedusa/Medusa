(function($) {
    'use strict';

    $.Browser = {
        defaults: {
            title: 'Choose Directory',
            url: 'browser/',
            autocompleteURL: 'browser/complete',
            includeFiles: 0,
            showBrowseButton: true
        }
    };

    let fileBrowserDialog;
    let currentBrowserPath;
    let currentRequest = null;

    function browse(path, endpoint, includeFiles) {
        if (currentBrowserPath === path) {
            return;
        }

        currentBrowserPath = path;

        if (currentRequest) {
            currentRequest.abort();
        }

        fileBrowserDialog.dialog('option', 'dialogClass', 'browserDialog busy');
        fileBrowserDialog.dialog('option', 'closeText', ''); // This removes the "Close" text

        currentRequest = $.getJSON(endpoint, {
            path,
            includeFiles
        }, data => {
            fileBrowserDialog.empty();
            const firstVal = data[0];
            let i = 0;
            let link = null;
            data = $.grep(data, () => {
                return i++ !== 0;
            });

            $('<input type="text" class="form-control input-sm">')
                .val(firstVal.currentPath)
                .on('keypress', e => {
                    if (e.which === 13) {
                        browse(e.target.value, endpoint, includeFiles);
                    }
                })
                .appendTo(fileBrowserDialog)
                .fileBrowser({ showBrowseButton: false })
                .on('autocompleteselect', (e, ui) => {
                    browse(ui.item.value, endpoint, includeFiles);
                });

            const list = $('<ul>').appendTo(fileBrowserDialog);
            $.each(data, (i, entry) => {
                link = $('<a href="javascript:void(0)">').on('click', () => {
                    if (entry.isFile) {
                        currentBrowserPath = entry.path;
                        $('.browserDialog .ui-button:contains("Ok")').click();
                    } else {
                        browse(entry.path, endpoint, includeFiles);
                    }
                }).text(entry.name);
                if (entry.isFile) {
                    link.prepend('<span class="ui-icon ui-icon-blank"></span>');
                } else {
                    link.prepend('<span class="ui-icon ui-icon-folder-collapsed"></span>').on('mouseenter', function() {
                        $('span', this).addClass('ui-icon-folder-open');
                    }).on('mouseleave', function() {
                        $('span', this).removeClass('ui-icon-folder-open');
                    });
                }
                link.appendTo(list);
            });
            $('a', list).wrap('<li class="ui-state-default ui-corner-all">');
            fileBrowserDialog.dialog('option', 'dialogClass', 'browserDialog');
        });
    }

    $.fn.nFileBrowser = function(callback, options) {
        options = $.extend({}, $.Browser.defaults, options);

        if (fileBrowserDialog) {
            // The title may change, even if fileBrowserDialog already exists
            fileBrowserDialog.dialog('option', 'title', options.title);
        } else {
            // Make a fileBrowserDialog object if one doesn't exist already
            // set up the jquery dialog
            fileBrowserDialog = $('<div class="fileBrowserDialog" style="display:hidden"></div>').appendTo('body').dialog({
                dialogClass: 'browserDialog',
                title: options.title,
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
        }

        fileBrowserDialog.dialog('option', 'buttons', [{
            text: 'Ok',
            class: 'btn-medusa',
            click() {
                // Store the browsed path to the associated text field
                callback(currentBrowserPath, options);
                $(this).dialog('close');
            }
        }, {
            text: 'Cancel',
            class: 'btn-medusa',
            click() {
                $(this).dialog('close');
            }
        }]);

        // Set up the browser and launch the dialog
        let initialDir = '';
        if (options.initialDir) {
            initialDir = options.initialDir;
        }

        browse(initialDir, options.url, options.includeFiles);
        fileBrowserDialog.dialog('open');

        return false;
    };

    $.fn.fileBrowser = function(options) {
        options = $.extend({}, $.Browser.defaults, options);
        // Text field used for the result
        options.field = $(this);

        if (options.field.autocomplete && options.autocompleteURL) {
            let query = '';
            options.field.autocomplete({
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
        // If the text field is empty and we're given a key then populate it with the last browsed value from localStorage
        try {
            ls = Boolean(localStorage.getItem);
        } catch (err) {
            console.log(err);
        }
        if (ls && options.key) {
            path = localStorage['fileBrowser-' + options.key];
        }
        if (options.key && options.field.val().length === 0 && (path)) {
            options.field.val(path);
        }

        const callback = (path, options) => {
            // Store the browsed path to the associated text field
            options.field.val(path);

            // Use a localStorage to remember for next time -- no ie6/7
            if (ls && options.key) {
                localStorage['fileBrowser-' + options.key] = path;
            }
        };

        options.field.addClass('fileBrowserField');
        if (options.showBrowseButton) {
            // Append the browse button and give it a click behaviour
            options.field.after(
                $('<input type="button" value="Browse&hellip;" class="btn-medusa btn-inline fileBrowser">').on('click', function() {
                    const initialDir = options.field.val() || (options.key && path) || '';
                    const optionsWithInitialDir = $.extend({}, options, { initialDir });
                    $(this).nFileBrowser(callback, optionsWithInitialDir);
                    return false;
                })
            );
        }
        return options.field;
    };
})(jQuery);
