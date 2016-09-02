MEDUSA.home.restart = function() {
    var currentPid = $('.messages').attr('current-pid');
    var defaultPage = $('.messages').attr('default-page');
    var checkIsAlive = setInterval(function() {
        $.get('home/is_alive/', function(data) {
            if (data.msg.toLowerCase() === 'nope') {
                // if it's still initializing then just wait and try again
                $('#restart_message').show();
            } else if (currentPid === '' || data.msg === currentPid) {
                $('#shut_down_loading').hide();
                $('#shut_down_success').show();
                currentPid = data.msg;
            } else {
                clearInterval(checkIsAlive);
                $('#restart_loading').hide();
                $('#restart_success').show();
                $('#refresh_message').show();
                setTimeout(function() {
                    window.location = defaultPage + '/';
                }, 5000);
            }
        }, 'jsonp');
    }, 100);
};
