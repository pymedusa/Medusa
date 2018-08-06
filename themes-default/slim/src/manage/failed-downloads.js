import $ from 'jquery';
import 'tablesorter'; // eslint-disable-line import/no-unassigned-import

export default () => {
    $('#failedTable:has(tbody tr)').tablesorter({
        widgets: ['zebra'],
        sortList: [],
        headers: { 3: { sorter: false } }
    });

    $('#limit').on('change', event => {
        window.location.href = $('base').attr('href') + 'manage/failedDownloads/?limit=' + $(event.currentTarget).val();
    });

    $('#submitMassRemove').on('click', () => {
        const removeArr = [];

        $('.removeCheck').each((index, element) => {
            if (element.checked === true) {
                removeArr.push($(element).attr('id').split('-')[1]);
            }
        });

        if (removeArr.length === 0) {
            return false;
        }

        window.location.href = $('base').attr('href') + 'manage/failedDownloads?toRemove=' + removeArr.join('|');
    });

    if ($('.removeCheck').length !== 0) {
        $('.removeCheck').each((index, element) => {
            let lastCheck = null;
            $(element).on('click', event => {
                if (!lastCheck || !event.shiftKey) {
                    lastCheck = this;
                    return;
                }

                const check = event.currentTarget;
                let found = 0;

                $(name + ':visible').each((index, element) => {
                    if (found === 1) {
                        element.checked = lastCheck.checked;
                    }
                    if (found === 2) {
                        return false;
                    }

                    if (element === check || element === lastCheck) {
                        found++;
                    }
                });
            });
        });
    }
};
