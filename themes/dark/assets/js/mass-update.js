$(document).ready(() => {
    $('.submitMassEdit').on('click', () => {
        const editArr = [];

        $('.editCheck').each(function() {
            if (this.checked === true) {
                editArr.push(`${$(this).attr('data-indexer-name')}${$(this).attr('data-series-id')}`);
            }
        });

        if (editArr.length === 0) {
            return;
        }

        const submitForm = $(
            '<form method=\'post\' action=\'' + $('base').attr('href') + 'manage/massEdit\'>' +
            '<input type=\'hidden\' name=\'toEdit\' value=\'' + editArr.join('|') + '\'/>' +
            '</form>'
        );
        submitForm.appendTo('body');

        submitForm.submit();
    });

    $('.submitMassUpdate').on('click', function() {
        const updateArr = [];
        const refreshArr = [];
        const renameArr = [];
        const subtitleArr = [];
        const deleteArr = [];
        const removeArr = [];
        const metadataArr = [];
        const imageUpdateArr = [];

        const indexerName = $(this).attr('data-indexer-name');
        const seriesId = $(this).attr('data-series-id');

        $('.updateCheck').each(function() {
            if (this.checked === true) {
                updateArr.push(`${$(this).attr('data-indexer-name')}${$(this).attr('data-series-id')}`);
            }
        });

        $('.refreshCheck').each(function() {
            if (this.checked === true) {
                refreshArr.push(`${$(this).attr('data-indexer-name')}${$(this).attr('data-series-id')}`);
            }
        });

        $('.renameCheck').each(function() {
            if (this.checked === true) {
                renameArr.push(`${$(this).attr('data-indexer-name')}${$(this).attr('data-series-id')}`);
            }
        });

        $('.subtitleCheck').each(function() {
            if (this.checked === true) {
                subtitleArr.push(`${$(this).attr('data-indexer-name')}${$(this).attr('data-series-id')}`);
            }
        });

        $('.removeCheck').each(function() {
            if (this.checked === true) {
                removeArr.push(`${$(this).attr('data-indexer-name')}${$(this).attr('data-series-id')}`);
            }
        });

        $('.imageCheck').each(function() {
            if (this.checked === true) {
                imageUpdateArr.push(`${$(this).attr('data-indexer-name')}${$(this).attr('data-series-id')}`);
            }
        });

        let deleteCount = 0;

        $('.deleteCheck').each(function() {
            if (this.checked === true) {
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
                    $('.deleteCheck').each(function() {
                        if (this.checked === true) {
                            deleteArr.push(`${indexerName}${seriesId}`);
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

        $(name).on('click', function(event) {
            if (!lastCheck || !event.shiftKey) {
                lastCheck = this;
                return;
            }

            const check = this;
            let found = 0;

            $(name).each(function() {
                if (found === 1) {
                    if (!this.disabled) {
                        this.checked = lastCheck.checked;
                    }
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
});
