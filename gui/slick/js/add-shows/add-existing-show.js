MEDUSA.addShows.addExistingShow = function() {
    $('#tableDiv').on('click', '#checkAll', function() {
        var seasCheck = this;
        $('.dirCheck').each(function() {
            this.checked = seasCheck.checked;
        });
    });

    // jquery extend function
    $.extend({
        redirectPost: function(location, args) {
            var form = '';
            $.each( args, function( key, value ) {
                if (typeof(value) === 'object') {
                    $.each( value, function( key, subValue ) {
                        form += '<input type="hidden" name="'+key+'" value="'+subValue+'">';
                    });
                } else {
                    form += '<input type="hidden" name="'+key+'" value="'+value+'">';
                }
            });
            $('<form action="'+location+'" method="POST">'+form+'</form>').appendTo('body').submit();
        }
    });

    $('#submitShowDirs').on('click', function() {
        var dirArr = {'submitListOfShows' : [], 'promptForSettings': ''};
        $('.dirCheck').each(function() {
            if (this.checked === true) {
                var existingIndexerId = $(this).attr('data-existing-indexer-id');
                var showName = $(this).attr('data-show-name');
                var existingIndexer = $(this).attr('data-existing-indexer');
                var selectedIndexer = $(this).closest('tr').find('select').val();
                var showDir = $(this).attr('data-show-dir');
                dirArr.submitListOfShows.push({'existingIndexerId': existingIndexerId, 'showDir': showDir,
                    'showName': showName, 'existingIndexer': existingIndexer, 'selectedIndexer': selectedIndexer});
            }
        });

        if (dirArr.length === 0) {
            return false;
        }

        dirArr.promptForSettings = $('#promptForSettings').prop('checked') ? 'on' : 'off';
        $.ajax({
            type: 'POST',
            url: 'addShows/addExistingShows',
            data: JSON.stringify(dirArr),
          })
          .success(function(response) {
              if (response) {
                  $.redirectPost('/addShows/newShow', JSON.parse(response));
              }
          });
    });

    function loadContent() {
        var url = '';
        $('.dir_check').each(function(i, w) {
            if ($(w).is(':checked')) {
                if (url.length) {
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
