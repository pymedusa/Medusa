$(document).ready(() => {
    $(document.body).on('click', '.submitMassEdit', () => {
        const editArr = [];

        $('.editCheck').each((index, element) => {
            if (element.checked === true) {
                editArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
            }
        });

        if (editArr.length === 0) {
            return;
        }

        const submitForm = $('<form method=\'post\' action=\'' + $('base').attr('href') + 'manage/massEdit\'>' +
            '<input type=\'hidden\' name=\'toEdit\' value=\'' + editArr.join('|') + '\'/>' +
            '</form>');
        submitForm.appendTo('body');

        submitForm.submit();
    });

    $(document.body).on('click', '.submitMassUpdate', () => {
        const updateArr = [];
        const refreshArr = [];
        const renameArr = [];
        const subtitleArr = [];
        const deleteArr = [];
        const removeArr = [];
        const metadataArr = [];
        const imageUpdateArr = [];

        $('.updateCheck').each((index, element) => {
            if (element.checked === true) {
                updateArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
            }
        });

        $('.refreshCheck').each((index, element) => {
            if (element.checked === true) {
                refreshArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
            }
        });

        $('.renameCheck').each((index, element) => {
            if (element.checked === true) {
                renameArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
            }
        });

        $('.subtitleCheck').each((index, element) => {
            if (element.checked === true) {
                subtitleArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
            }
        });

        $('.removeCheck').each((index, element) => {
            if (element.checked === true) {
                removeArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
            }
        });

        $('.imageCheck').each((index, element) => {
            if (element.checked === true) {
                imageUpdateArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
            }
        });

        let deleteCount = 0;

        $('.deleteCheck').each((index, element) => {
            if (element.checked === true) {
                deleteCount++;
            }
        });

        const totalCount = [].concat.apply([], [updateArr, refreshArr, renameArr, subtitleArr, deleteArr, removeArr, metadataArr, imageUpdateArr]).length; // eslint-disable-line no-useless-call

        if (deleteCount >= 1) {
            $.confirm({
                title: 'Delete Shows',
                text: 'You have selected to delete ' + deleteCount + ' show(s).  Are you sure you wish to continue? All files will be removed from your system.',
                confirmButton: 'Yes',
                cancelButton: 'Cancel',
                dialogClass: 'modal-dialog',
                post: false,
                confirm() {
                    $('.deleteCheck').each((index, element) => {
                        if (element.checked === true) {
                            deleteArr.push(`${$(element).attr('data-indexer-name')}${$(element).attr('data-series-id')}`);
                        }
                    });
                    if (totalCount === 0) {
                        return false;
                    }
                    const params = $.param({
                        toUpdate: updateArr.join('|'),
                        toRefresh: refreshArr.join('|'),
                        toRename: renameArr.join('|'),
                        toSubtitle: subtitleArr.join('|'),
                        toDelete: deleteArr.join('|'),
                        toRemove: removeArr.join('|'),
                        toMetadata: metadataArr.join('|'),
                        toImageUpdate: imageUpdateArr.join('|')
                    });

                    window.location.href = $('base').attr('href') + 'manage/massUpdate?' + params;
                }
            });
        }

        if (totalCount === 0) {
            return false;
        }
        if (updateArr.length + refreshArr.length + renameArr.length + subtitleArr.length + deleteArr.length + removeArr.length + metadataArr.length + imageUpdateArr.length === 0) {
            return false;
        }
        const url = $('base').attr('href') + 'manage/massUpdate';
        const params = 'toUpdate=' + updateArr.join('|') + '&toRefresh=' + refreshArr.join('|') + '&toRename=' + renameArr.join('|') + '&toSubtitle=' + subtitleArr.join('|') + '&toDelete=' + deleteArr.join('|') + '&toRemove=' + removeArr.join('|') + '&toMetadata=' + metadataArr.join('|') + '&toImageUpdate=' + imageUpdateArr.join('|');
        $.post(url, params, () => {
            location.reload(true);
        });
    });

    ['.editCheck', '.updateCheck', '.refreshCheck', '.renameCheck', '.deleteCheck', '.removeCheck', '.imageCheck'].forEach(name => {
        let lastCheck = null;

        $(document.body).on('click', name, event => {
            if (!lastCheck || !event.shiftKey) {
                lastCheck = event.currentTarget;
                return;
            }

            const check = event.currentTarget;
            let found = 0;

            $(name).each((index, element) => {
                if (found === 1) {
                    if (!element.disabled) {
                        element.checked = lastCheck.checked;
                    }
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
});
