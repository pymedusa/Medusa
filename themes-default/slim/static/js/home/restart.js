MEDUSA.home.restart = function() {
    let currentPid = $('.messages').attr('current-pid');
    const defaultPage = $('.messages').attr('default-page');
    const checkIsAlive = setInterval(() => {
        // @TODO: Move to API
        $.get('home/is_alive/', data => {
            if (data.msg.toLowerCase() === 'nope') {
                // If it's still initializing then just wait and try again
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
                setTimeout(() => {
                    window.location = defaultPage + '/';
                }, 5000);
            }
        }, 'jsonp');
    }, 100);
};
