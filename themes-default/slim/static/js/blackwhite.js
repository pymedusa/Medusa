$(document).ready(() => {
    $('#removeW').on('click', () => {
        !$('#white option:selected').remove().appendTo('#pool'); // eslint-disable-line no-unused-expressions
    });

    $('#addW').on('click', () => {
        !$('#pool option:selected').remove().appendTo('#white'); // eslint-disable-line no-unused-expressions
    });

    $('#addB').on('click', () => {
        !$('#pool option:selected').remove().appendTo('#black'); // eslint-disable-line no-unused-expressions
    });

    $('#removeP').on('click', () => {
        !$('#pool option:selected').remove(); // eslint-disable-line no-unused-expressions
    });

    $('#removeB').on('click', () => {
        !$('#black option:selected').remove().appendTo('#pool'); // eslint-disable-line no-unused-expressions
    });

    $('#addToWhite').on('click', () => {
        const group = $('#addToPoolText').val();
        if (group !== '') {
            const option = $('<option>');
            option.prop('value', group);
            option.html(group);
            option.appendTo('#white');
            $('#addToPoolText').val('');
        }
    });

    $('#addToBlack').on('click', () => {
        const group = $('#addToPoolText').val();
        if (group !== '') {
            const option = $('<option>');
            option.prop('value', group);
            option.html(group);
            option.appendTo('#black');
            $('#addToPoolText').val('');
        }
    });
});
