// @TODO: Remove this when we fully drop support for IE > 8
// Avoid `console` errors in browsers that lack a console.
(function() { // eslint-disable-line wrap-iife
    var method;
    var noop = function noop() {}; // eslint-disable-line func-names
    var methods = [
        'assert', 'clear', 'count', 'debug', 'dir', 'dirxml', 'error',
        'exception', 'group', 'groupCollapsed', 'groupEnd', 'info', 'log',
        'markTimeline', 'profile', 'profileEnd', 'table', 'time', 'timeEnd',
        'timeStamp', 'trace', 'warn'
    ];
    var length = methods.length;
    window.console = window.console || {};
    var console = window.console;

    while (length--) {
        method = methods[length];

        // Only stub undefined methods.
        if (!console[method]) {
            console[method] = noop;
        }
    }
}());

$(document).ready(function() {
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
            var oldDefault = $('#' + $('#whichDefaultRootDir').val());
            oldDefault.text(oldDefault.text().substring(1));
        }

        $('#whichDefaultRootDir').val(which);
    }

    function syncOptionIDs() {
        // Re-sync option ids
        var i = 0;
        $('#rootDirs option').each(function() {
            $(this).prop('id', 'rd-' + (i++));
        });
    }

    function refreshRootDirs() {
        if ($('#rootDirs').length === 0) {
            /* Trigger change event as $.rootDirCheck() function is not
               always available when this section of code is called. */
            $('#rootDirs').trigger('change');
            return;
        }

        var doDisable = 'true';

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

        var dirString = '';
        if ($('#whichDefaultRootDir').val().length >= 4) {
            dirString = $('#whichDefaultRootDir').val().substr(3);
        }
        $('#rootDirs option').each(function() {
            if (dirString.length !== 0) {
                dirString += '|' + $(this).val();
            }
        });

        $('#rootDirText').val(dirString);
        // Manually trigger change event as setting .val directly doesn't
        $('#rootDirs').trigger('change');
    }

    function addRootDir(path) {
        if (path.length === 0) {
            return;
        }

        // Check if it's the first one
        var isDefault = false;
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
    }

    function editRootDir(path) {
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
    }

    $('#addRootDir').on('click', function() {
        $(this).nFileBrowser(addRootDir);
    });
    $('#editRootDir').on('click', function() {
        $(this).nFileBrowser(editRootDir, {
            initialDir: $('#rootDirs option:selected').val()
        });
    });

    $('#deleteRootDir').on('click', function() {
        if ($('#rootDirs option:selected').length !== 0) {
            var toDelete = $('#rootDirs option:selected');
            var newDefault = (toDelete.attr('id') === $('#whichDefaultRootDir').val());
            var deletedNum = $('#rootDirs option:selected').attr('id').substr(3);

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
                var oldDefaultNum = $('#whichDefaultRootDir').val().substr(3);
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

    $('#defaultRootDir').on('click', function() {
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
