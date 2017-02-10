MEDUSA.manage.backlogOverview = function() {
    $('#pickShow').on('change', function() {
        var id = $(this).val();
        if (id) {
            $('html,body').animate({scrollTop: $('#show-' + id).offset().top - 25}, 'slow');
        }
    });

    $('.forceBacklog').on('click', function(){
        $.get($(this).attr('href'));
        $(this).text('Searching...');
        return false;
    });
};
