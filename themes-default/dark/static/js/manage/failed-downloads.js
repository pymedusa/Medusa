MEDUSA.manage.failedDownloads = function() {
    $('#failedTable:has(tbody tr)').tablesorter({
        widgets: ['zebra'],
        sortList: [],
        headers: { 3: { sorter: false } }
    });
    $('#limit').on('change', function() {
        window.location.href = $('base').attr('href') + 'manage/failedDownloads/?limit=' + $(this).val();
    });

    $('#submitMassRemove').on('click', () => {
        const removeArr = [];

        $('.removeCheck').each(function() {
            if (this.checked === true) {
                removeArr.push($(this).attr('id').split('-')[1]);
            }
        });

        if (removeArr.length === 0) {
            return false;
        }

        window.location.href = $('base').attr('href') + 'manage/failedDownloads?toRemove=' + removeArr.join('|');
    });

    if ($('.removeCheck').length !== 0) {
        $('.removeCheck').each(name => {
            let lastCheck = null;
            $(name).click(function(event) {
                if (!lastCheck || !event.shiftKey) {
                    lastCheck = this;
                    return;
                }

                const check = this;
                let found = 0;

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
