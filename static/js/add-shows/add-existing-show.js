MEDUSA.addShows.addExistingShow = function() {
    // Hide the black/whitelist, because it can only be used for a single anime show
    $.updateBlackWhiteList(undefined);

    $('#tableDiv').on('click', '#checkAll', function() {
        var seasonCheck = this;
        $('.dirCheck').each(function() {
            this.checked = seasonCheck.checked;
        });
    });

    $('#submitShowDirs').on('click', function() {
        var dirArr = [];
        $('.dirCheck').each(function() {
            if (this.checked === true) {
                var originalIndexer = $(this).attr('data-indexer');
                var indexerId = '|' + $(this).attr('data-indexer-id');
                var showName = $(this).attr('data-show-name');
                var showDir = $(this).attr('data-show-dir');

                var indexer = $(this).closest('tr').find('select').val();
                if (originalIndexer !== indexer || originalIndexer === '0') {
                    indexerId = '';
                }
                dirArr.push(encodeURIComponent(indexer + '|' + showDir + indexerId + '|' + showName));
            }
        });

        if (dirArr.length === 0) {
            return false;
        }

        window.location.href = $('base').attr('href') + 'addShows/addExistingShows?promptForSettings=' + ($('#promptForSettings').prop('checked') ? 'on' : 'off') + '&shows_to_add=' + dirArr.join('&shows_to_add=');
    });

    function loadContent() {
        var url = '';
        $('.dir_check').each(function(i, w) {
            if ($(w).is(':checked')) {
                if (url.length !== 0) {
                    url += '&';
                }
                url += 'rootDir=' + encodeURIComponent($(w).attr('id'));
            }
        });

        $('#tableDiv').html('<img id="searchingAnim" src="images/loading32.gif" height="32" width="32" /> loading folders...');
        $.get('addShows/massAddTable/', url, function(data) {
            $('#tableDiv').html(data);
            $('#addRootDirTable').tablesorter({
                // sortList: [[1,0]],
                widgets: ['zebra'],
                headers: {
                    0: {sorter: false}
                }
            });
        });
    }

    var lastTxt = '';
    // @TODO this needs a real name, for now this fixes the issue of the page not loading at all,
    //       before I added this I couldn't get the directories to show in the table
    var a = function() {
        if (lastTxt === $('#rootDirText').val()) {
            return false;
        }
        lastTxt = $('#rootDirText').val();
        $('#rootDirStaticList').html('');
        $('#rootDirs option').each(function(i, w) {
            $('#rootDirStaticList').append('<li class="ui-state-default ui-corner-all"><input type="checkbox" class="cb dir_check" id="' + $(w).val() + '" checked=checked> <label for="' + $(w).val() + '"><b>' + $(w).val() + '</b></label></li>');
        });
        loadContent();
    };

    a();

    $('#rootDirText').on('change', a);

    $('#rootDirStaticList').on('click', '.dir_check', loadContent);

    $('#tableDiv').on('click', '.showManage', function(event) {
        event.preventDefault();
        $('#tabs').tabs('option', 'active', 0);
        $('html,body').animate({scrollTop: 0}, 1000);
    });
};
