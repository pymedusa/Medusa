(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){


$(document).ready(() => {
    $('.submitMassEdit').on('click', () => {
        const editArr = [];

        $('.editCheck').each(function () {
            if (this.checked === true) {
                editArr.push($(this).attr('id').split('-')[1]);
            }
        });

        if (editArr.length === 0) {
            return;
        }

        const submitForm = $(`
            <form method="post" action="${$('base').attr('href')}manage/massEdit">
                <input type="hidden" name="toEdit" value="${editArr.join('|')}"/>
            </form>
        `);
        submitForm.appendTo('body');

        submitForm.submit();
    });

    $('.submitMassUpdate').on('click', () => {
        const updateArr = [];
        const refreshArr = [];
        const renameArr = [];
        const subtitleArr = [];
        const deleteArr = [];
        const removeArr = [];
        const metadataArr = [];

        $('.updateCheck').each(function () {
            if (this.checked === true) {
                updateArr.push($(this).attr('id').split('-')[1]);
            }
        });

        $('.refreshCheck').each(function () {
            if (this.checked === true) {
                refreshArr.push($(this).attr('id').split('-')[1]);
            }
        });

        $('.renameCheck').each(function () {
            if (this.checked === true) {
                renameArr.push($(this).attr('id').split('-')[1]);
            }
        });

        $('.subtitleCheck').each(function () {
            if (this.checked === true) {
                subtitleArr.push($(this).attr('id').split('-')[1]);
            }
        });

        $('.removeCheck').each(function () {
            if (this.checked === true) {
                removeArr.push($(this).attr('id').split('-')[1]);
            }
        });

        let deleteCount = 0;

        $('.deleteCheck').each(function () {
            if (this.checked === true) {
                deleteCount++;
            }
        });

        const totalCount = [].concat.apply([], [updateArr, refreshArr, renameArr, subtitleArr, deleteArr, removeArr, metadataArr]).length; // eslint-disable-line no-useless-call

        if (deleteCount >= 1) {
            window.$.confirm({
                title: 'Delete Shows',
                text: 'You have selected to delete ' + deleteCount + ' show(s).  Are you sure you wish to continue? All files will be removed from your system.',
                confirmButton: 'Yes',
                cancelButton: 'Cancel',
                dialogClass: 'modal-dialog',
                post: false,
                confirm() {
                    $('.deleteCheck').each(function () {
                        if (this.checked === true) {
                            deleteArr.push($(this).attr('id').split('-')[1]);
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
                        toMetadata: metadataArr.join('|')
                    });

                    window.location.href = $('base').attr('href') + 'manage/massUpdate?' + params;
                }
            });
        }

        if (totalCount === 0) {
            return false;
        }
        if (updateArr.length + refreshArr.length + renameArr.length + subtitleArr.length + deleteArr.length + removeArr.length + metadataArr.length === 0) {
            return false;
        }
        const url = $('base').attr('href') + 'manage/massUpdate';
        const params = 'toUpdate=' + updateArr.join('|') + '&toRefresh=' + refreshArr.join('|') + '&toRename=' + renameArr.join('|') + '&toSubtitle=' + subtitleArr.join('|') + '&toDelete=' + deleteArr.join('|') + '&toRemove=' + removeArr.join('|') + '&toMetadata=' + metadataArr.join('|');
        $.post(url, params, () => {
            location.reload(true);
        });
    });

    ['.editCheck', '.updateCheck', '.refreshCheck', '.renameCheck', '.deleteCheck', '.removeCheck'].forEach(name => {
        let lastCheck = null;

        $(name).on('click', function (event) {
            if (!lastCheck || !event.shiftKey) {
                lastCheck = this;
                return;
            }

            const check = this;
            let found = 0;

            $(name).each(function () {
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

},{}]},{},[1]);

//# sourceMappingURL=mass-update.js.map
