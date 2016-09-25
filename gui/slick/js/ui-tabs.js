$.fn.uiTabs = function(defaultTab) {
    // http://stackoverflow.com/a/9282379/2311366
    (function(namespace) {
        if ('replaceState' in history) {
            namespace.replaceHash = function(newhash) {
                var base = document.location.href.split('#')[0];
                if ((String(newhash)).charAt(0) !== '#') {
                    newhash = '#' + newhash;
                }
                history.replaceState('', '', base + newhash);
            };
        } else {
            var hash = location.hash;
            namespace.replaceHash = function(newhash) {
                var base = document.location.href.split('#')[0];
                if (location.hash !== hash) {
                    history.back();
                }
                location.hash = base + newhash;
            };
        }
    })(window);

    $(this).addClass('ui-widget ui-widget-content ui-corner-all');

    var tabsNav = $(this).children('ul');
    var tabs = tabsNav.children('li');

    if (tabs.length) {
        tabsNav.addClass('ui-tabs-nav ui-helper-reset ui-helper-clearfix ui-widget-header ui-corner-all').attr('role', 'tablist');
        tabs.addClass('ui-state-default ui-corner-top');
        tabs.children('a').addClass('ui-tabs-anchor').attr('role', 'tab');
        $('[data-tab-id]').addClass('ui-tabs-panel ui-widget-content ui-corner-bottom');

        defaultTab = defaultTab || tabs.find('a').eq(0).attr('href').split('#')[1];

        var switchTab = function(tabId) {
            var toggleClasses = 'ui-tabs-active ui-state-active';

            $('[data-tab-id]').hide();
            tabs.removeClass(toggleClasses);

            $('[data-tab-id="' + tabId + '"]').show();
            tabs.children('a[href$="#' + tabId + '"]').parent().addClass(toggleClasses);

            window.replaceHash(tabId);
        };

        tabs.on('click', function(e) {
            e.preventDefault();
            switchTab($(this).children('a').attr('href').split('#')[1]);
        });

        // If we have a tab with the same id as the hash switch to it
        var hashTab = '[data-tab-id="' + window.location.hash.split('#')[1] + '"]';
        if ($(hashTab).length && $(hashTab).parent('.ui-tabs').length) {
            switchTab(window.location.hash.split('#')[1]);
        } else {
            switchTab(defaultTab);
        }
    }
};
