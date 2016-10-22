MEDUSA.manage.failedDownloads = function() {
    $('#failedTable:has(tbody tr)').tablesorter({
        widgets: ['zebra'],
        sortList: [],
        headers: {3: {sorter: false}}
    });
    $('#limit').on('change', function() {
        window.location.href = 'manage/failedDownloads/?limit=' + $(this).val();
    });

    $('#submitMassRemove').on('click', function() {
        var removeArr = [];

        $('.removeCheck').each(function() {
            if (this.checked === true) {
                removeArr.push($(this).attr('id').split('-')[1]);
            }
        });

        if (removeArr.length === 0) {
            return false;
        }

        window.location.href = 'manage/failedDownloads?toRemove=' + removeArr.join('|');
    });

    if ($('.removeCheck').length !== 0) {
        $('.removeCheck').each(function(name) {
            var lastCheck = null;
            $(name).click(function(event) {
                if (!lastCheck || !event.shiftKey) {
                    lastCheck = this;
                    return;
                }

                var check = this;
                var found = 0;

                $(name + ':visible').each(function() {
                    if (found === 1) {
                        this.checked = lastCheck.checked;
                    }
                    if (found === 2) {
                        return false;
                    }

                    if (this === check || this === lastCheck) {
                        found++;
                    }
                });
            });
        });
    }
};
