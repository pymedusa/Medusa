MEDUSA.addShows.addExistingShow = function() {
    // Hide the black/whitelist, because it can only be used for a single anime show
    $.updateBlackWhiteList(undefined);

    $('#tableDiv').on('click', '#checkAll', function() {
        const seasonCheck = this;
        $('.dirCheck').each(function() {
            this.checked = seasonCheck.checked;
        });
    });

    $('#submitShowDirs').on('click', () => {
        const dirArr = [];
        $('.dirCheck').each(function() {
            if (this.checked === true) {
                const originalIndexer = $(this).attr('data-indexer');
                let indexerId = '|' + $(this).attr('data-indexer-id');
                const showName = $(this).attr('data-show-name');
                const showDir = $(this).attr('data-show-dir');

                const indexer = $(this).closest('tr').find('select').val();
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
        let url = '';
        $('.dir_check').each((i, w) => {
            if ($(w).is(':checked')) {
                if (url.length !== 0) {
                    url += '&';
                }
                url += 'rootDir=' + encodeURIComponent($(w).attr('id'));
            }
        });

        $('#tableDiv').html('<img id="searchingAnim" src="images/loading32.gif" height="32" width="32" /> loading folders...');
        $.get('addShows/massAddTable/', url, data => {
            $('#tableDiv').html(data);
            $('#addRootDirTable').tablesorter({
                // SortList: [[1,0]],
                widgets: ['zebra'],
                headers: {
                    0: { sorter: false }
                }
            });
        });
    }

    let lastTxt = '';
    // @TODO this needs a real name, for now this fixes the issue of the page not loading at all,
    //       before I added this I couldn't get the directories to show in the table
    const a = function() {
        if (lastTxt === $('#rootDirText').val()) {
            return false;
        }
        lastTxt = $('#rootDirText').val();
        $('#rootDirStaticList').html('');
        $('#rootDirs option').each((i, w) => {
            $('#rootDirStaticList').append('<li class="ui-state-default ui-corner-all"><input type="checkbox" class="cb dir_check" id="' + $(w).val() + '" checked=checked> <label for="' + $(w).val() + '"><b>' + $(w).val() + '</b></label></li>');
        });
        loadContent();
    };

    a();

    $('#rootDirText').on('change', a);

    $('#rootDirStaticList').on('click', '.dir_check', loadContent);

    $('#tableDiv').on('click', '.showManage', event => {
        event.preventDefault();
        $('#tabs').tabs('option', 'active', 0);
        $('html,body').animate({ scrollTop: 0 }, 1000);
    });
};
