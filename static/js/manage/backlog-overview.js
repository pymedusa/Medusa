MEDUSA.manage.backlogOverview = function() {
    $('#pickShow').on('change', function() {
        var id = $(this).val();
        if (id) {
            $('html,body').animate({scrollTop: $('#show-' + id).offset().top - 25}, 'slow');
        }
    });

    $.ajaxEpSearch({
        colorRow: false
    });

    $('.forceBacklog').on('click', function(){
        $.get($(this).attr('href'));
        $(this).text('Searching...');
        return false;
    });

    $('.epArchive').on('click', function(event) {
        event.preventDefault();
        var img = $(this).children('img[data-ep-archive]');
        img.prop('title', 'Archiving');
        img.prop('alt', 'Archiving');
        img.prop('src', 'images/loading16.gif');
        var url = $(this).prop('href');
        $.getJSON(url, function(data) {
            // if they failed then just put the red X
            if (data.result.toLowerCase() === 'success') {
                img.prop('src', 'images/yes16.png');
                setTimeout(function() {
                    img.parent().parent().parent().remove()
                }, 3000)
            } else {
                img.prop('src', 'images/no16.png');
            }
            return false;
        });
    });
};
