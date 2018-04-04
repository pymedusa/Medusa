$(document).ready(() => {
    function findDirIndex(which) {
        const dirParts = which.split('_');
        return dirParts[dirParts.length - 1];
    }

    function editRootDir(path, options) {
        $('#new_root_dir_' + options.whichId).val(path);
        $('#new_root_dir_' + options.whichId).change();
    }

    $('.new_root_dir').on('change', function() {
        const curIndex = findDirIndex($(this).attr('id'));
        $('#display_new_root_dir_' + curIndex).html('<b>' + $(this).val() + '</b>');
    });

    $('.edit_root_dir').on('click', function(event) {
        event.preventDefault();
        const curIndex = findDirIndex($(this).attr('id'));
        const initialDir = $('#new_root_dir_' + curIndex).val();
        $(this).nFileBrowser(editRootDir, {
            initialDir,
            whichId: curIndex
        });
    });

    $('.delete_root_dir').on('click', function() {
        const curIndex = findDirIndex($(this).attr('id'));
        $('#new_root_dir_' + curIndex).val(null);
        $('#display_new_root_dir_' + curIndex).html('<b>DELETED</b>');
    });
});
