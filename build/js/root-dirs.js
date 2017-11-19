(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
// @TODO: Remove this when we fully drop support for IE > 8
// Avoid `console` errors in browsers that lack a console.
(function () {
    // eslint-disable-line wrap-iife
    const noop = () => {};
    const methods = ['assert', 'clear', 'count', 'debug', 'dir', 'dirxml', 'error', 'exception', 'group', 'groupCollapsed', 'groupEnd', 'info', 'log', 'markTimeline', 'profile', 'profileEnd', 'table', 'time', 'timeEnd', 'timeStamp', 'trace', 'warn'];
    // eslint-disable-next-line no-multi-assign
    const console = window.console = window.console || {};

    let method;
    let length = methods.length;
    while (length--) {
        method = methods[length];

        // Only stub undefined methods.
        if (!console[method]) {
            console[method] = noop;
        }
    }
})();

$(document).ready(() => {
    function setDefault(which, force) {
        if (which !== undefined && which.length === 0) {
            return;
        }

        if ($('#whichDefaultRootDir').val() === which && force !== true) {
            return;
        }

        // Put an asterisk on the text
        if ($('#' + which).text().charAt(0) !== '*') {
            $('#' + which).text('*' + $('#' + which).text());
        }

        // If there's an existing one then take the asterisk off
        if ($('#whichDefaultRootDir').val() && force !== true) {
            const oldDefault = $('#' + $('#whichDefaultRootDir').val());
            oldDefault.text(oldDefault.text().substring(1));
        }

        $('#whichDefaultRootDir').val(which);
    }

    const syncOptionIDs = () => {
        // Re-sync option ids
        let i = 0;
        $('#rootDirs option').each(function () {
            $(this).prop('id', 'rd-' + i++);
        });
    };

    const refreshRootDirs = () => {
        if ($('#rootDirs').length === 0) {
            /* Trigger change event as $.rootDirCheck() function is not
               always available when this section of code is called. */
            $('#rootDirs').trigger('change');
            return;
        }

        let doDisable = 'true';

        // Re-sync option ids
        syncOptionIDs();

        // If nothing's selected then select the default
        if ($('#rootDirs option:selected').length === 0 && $('#whichDefaultRootDir').val().length !== 0) {
            $('#' + $('#whichDefaultRootDir').val()).prop('selected', true);
        }

        // If something's selected then we have some behavior to figure out
        if ($('#rootDirs option:selected').length !== 0) {
            doDisable = '';
        }

        // Update the elements
        $('#deleteRootDir').prop('disabled', doDisable);
        $('#defaultRootDir').prop('disabled', doDisable);
        $('#editRootDir').prop('disabled', doDisable);

        let dirString = '';
        if ($('#whichDefaultRootDir').val().length >= 4) {
            dirString = $('#whichDefaultRootDir').val().substr(3);
        }
        $('#rootDirs option').each(function () {
            if (dirString.length !== 0) {
                dirString += '|' + $(this).val();
            }
        });

        $('#rootDirText').val(dirString);
        // Manually trigger change event as setting .val directly doesn't
        $('#rootDirs').trigger('change');
    };

    const addRootDir = path => {
        if (path.length === 0) {
            return;
        }

        // Check if it's the first one
        let isDefault = false;
        if ($('#whichDefaultRootDir').val().length === 0) {
            isDefault = true;
        }

        $('#rootDirs').append('<option value="' + path + '">' + path + '</option>');

        syncOptionIDs();

        if (isDefault) {
            setDefault($('#rootDirs option').attr('id'));
        }

        refreshRootDirs();
        $.get('config/general/saveRootDirs', {
            rootDirString: $('#rootDirText').val()
        });
    };

    const editRootDir = path => {
        if (path.length === 0) {
            return;
        }

        // As long as something is selected
        if ($('#rootDirs option:selected').length !== 0) {
            // Update the selected one with the provided path
            if ($('#rootDirs option:selected').attr('id') === $('#whichDefaultRootDir').val()) {
                $('#rootDirs option:selected').text('*' + path);
            } else {
                $('#rootDirs option:selected').text(path);
            }
            $('#rootDirs option:selected').val(path);
        }

        refreshRootDirs();
        $.get('config/general/saveRootDirs', {
            rootDirString: $('#rootDirText').val()
        });
    };

    $('#addRootDir').on('click', function () {
        $(this).nFileBrowser(addRootDir);
    });
    $('#editRootDir').on('click', function () {
        $(this).nFileBrowser(editRootDir, {
            initialDir: $('#rootDirs option:selected').val()
        });
    });

    $('#deleteRootDir').on('click', () => {
        if ($('#rootDirs option:selected').length !== 0) {
            const toDelete = $('#rootDirs option:selected');
            const newDefault = toDelete.attr('id') === $('#whichDefaultRootDir').val();
            const deletedNum = $('#rootDirs option:selected').attr('id').substr(3);

            toDelete.remove();
            syncOptionIDs();

            if (newDefault) {
                console.log('new default when deleting');

                // We deleted the default so this isn't valid anymore
                $('#whichDefaultRootDir').val('');

                // If we're deleting the default and there are options left then pick a new default
                if ($('#rootDirs option').length !== 0) {
                    setDefault($('#rootDirs option').attr('id'));
                }
            } else if ($('#whichDefaultRootDir').val().length !== 0) {
                const oldDefaultNum = $('#whichDefaultRootDir').val().substr(3);
                if (oldDefaultNum > deletedNum) {
                    $('#whichDefaultRootDir').val('rd-' + (oldDefaultNum - 1));
                }
            }
        }
        refreshRootDirs();
        $.get('config/general/saveRootDirs', {
            rootDirString: $('#rootDirText').val()
        });
    });

    $('#defaultRootDir').on('click', () => {
        if ($('#rootDirs option:selected').length !== 0) {
            setDefault($('#rootDirs option:selected').attr('id'));
        }
        refreshRootDirs();
        $.get('config/general/saveRootDirs', {
            rootDirString: $('#rootDirText').val()
        });
    });
    $('#rootDirs').click(refreshRootDirs);

    // Set up buttons on page load
    syncOptionIDs();
    setDefault($('#whichDefaultRootDir').val(), true);
    refreshRootDirs();
});

},{}]},{},[1]);

//# sourceMappingURL=root-dirs.js.map
